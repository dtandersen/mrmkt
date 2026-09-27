"""BDD coverage for the live WatchPrices command and CLI entrypoint."""

import os
import select
import signal
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from shlex import split
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from hamcrest import assert_that, equal_to
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.ranges import ListRanges
from mrmkt.command.watch import Quote, WatchPrices, WatchPricesRequest
from mrmkt.common.clock import ClockStub
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import Trigger

scenarios(
    "features/cli/watch.feature",
    "features/command/watch.feature",
)

ROOT = Path(__file__).parent.parent
DRIVER = Path(__file__).parent / "watch_blocking_driver.py"

START = date(2022, 1, 3)
N_BARS = 60


@pytest.fixture
def watch_context(financial_repository):
    clock = ClockStub()
    clock.set_time(date(2022, 4, 1))
    context = SimpleNamespace(result=None)
    context.cli_result = None
    context.clock = clock
    context.emitted = []
    context.streamed = None
    context.trigger_id = None
    context.proc = None
    context.child_output = ""

    class CliPriceSource:
        def subscribe(self, symbols, feed, *, on_quote) -> None:
            context.streamed = (list(symbols), feed)

    context.price_source = CliPriceSource()
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        clock=clock,
        watch_price_source=context.price_source,
    )
    yield context
    proc = context.proc
    if proc is not None and proc.poll() is None:
        proc.kill()
        proc.wait()


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


def _business_days(start: date, n: int) -> list[date]:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _ensure_ticker(local, symbol, exchange="NASDAQ") -> None:
    if symbol not in {ticker.ticker for ticker in local.get_tickers()}:
        local.add_ticker(Ticker(ticker=symbol, exchange=exchange, type="us_equity"))


def _add_climb(local, symbol, dip: bool) -> None:
    _ensure_ticker(local, symbol)
    closes = [100.0 * (1.002**i) for i in range(N_BARS)]
    if dip:
        for pos, factor in ((45, 0.90), (46, 0.93), (47, 0.97)):
            closes[pos] *= factor
    for day, close in zip(_business_days(START, N_BARS), closes, strict=True):
        low = close * (0.99 if dip else 0.995)
        local.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=close,
                high=close * 1.005,
                low=low,
                close=close,
                volume=1000.0,
            )
        )


def _add_short_climb(local, symbol) -> None:
    _ensure_ticker(local, symbol)
    price = 100.0
    for day in _business_days(START, 5):
        local.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=1000.0,
            )
        )
        price *= 1.002


def _add_trigger(repository, name: str, symbol: str, frequency: str = "once_per_rearm"):
    return repository.add_trigger(
        Trigger(
            id=None,
            name=name,
            symbol=symbol,
            indicator="risk-range",
            operator="crossing-down",
            frequency=frequency,
        )
    )


@given("the alerts catalog contains these symbols:")
def alerts_catalog_contains_symbols(watch_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse("{symbol} has a 60-bar climb with a dip"))
def symbol_has_dip(financial_repository, symbol):
    _add_climb(financial_repository, symbol, dip=True)


@given(parsers.parse("{symbol} has a 60-bar steady climb"))
def symbol_has_steady_climb(financial_repository, symbol):
    _add_climb(financial_repository, symbol, dip=False)


@given(parsers.parse("{symbol} has a 5-bar climb"))
def symbol_has_short_climb(financial_repository, symbol):
    _add_short_climb(financial_repository, symbol)


def _given_trigger(watch_context, financial_repository, name, symbol, frequency):
    trigger = _add_trigger(financial_repository, name, symbol, frequency)
    assert trigger.frequency == frequency
    watch_context.trigger_id = trigger.id


@given(parsers.parse('stored trigger "{name}" watches "{symbol}" crossing down'))
def stored_trigger_watches_symbol(watch_context, financial_repository, name, symbol):
    _given_trigger(watch_context, financial_repository, name, symbol, "once_per_rearm")


@given(parsers.parse('stored trigger "{name}" watches "{symbol}" crossing down once'))
def stored_once_trigger_watches_symbol(
    watch_context, financial_repository, name, symbol
):
    _given_trigger(watch_context, financial_repository, name, symbol, "once")


@when(parsers.parse('I execute "{command}"'))
def execute_watch_command(watch_context, command):
    args = split(command)
    watch_context.cli_result = CliRunner().invoke(
        cli.app, args[1:], obj=watch_context.deps
    )


def _watch(
    watch_context,
    financial_repository,
    interrupt_stream=False,
    scripted_quotes=None,
    **kwargs,
):
    class FakePriceSource:
        """Test source that records subscriptions and emits scripted prices."""

        def subscribe(self, symbols, feed, *, on_quote) -> None:
            watch_context.streamed = (list(symbols), feed)
            if interrupt_stream:
                raise KeyboardInterrupt
            for symbol, bid, ask, timestamp in scripted_quotes or []:
                on_quote(Quote(symbol=symbol, bid=bid, ask=ask, timestamp=timestamp))

    def emit(line: str) -> None:
        watch_context.emitted.append(line)

    command = WatchPrices(
        financial_repository,
        FakePriceSource(),
        emit,
        ranges=ListRanges(financial_repository, watch_context.clock),
    )
    execute_watch = command.execute
    return execute_watch(WatchPricesRequest(**kwargs))


@when("I watch with no selection in live mode")
def watch_bare(watch_context, financial_repository):
    watch_context.result = _watch(watch_context, financial_repository)


@when(parsers.parse('I watch symbols "{first}" and "{second}" in live mode'))
def watch_two_symbols(watch_context, financial_repository, first, second):
    watch_context.result = _watch(
        watch_context, financial_repository, symbols=[first, second]
    )


@when(parsers.parse('I watch symbol "{symbol}" plus its stored trigger'))
def watch_symbol_and_trigger(watch_context, financial_repository, symbol):
    watch_context.result = _watch(
        watch_context,
        financial_repository,
        symbols=[symbol],
        trigger_ids=[watch_context.trigger_id],
    )


@when(parsers.parse("I watch trigger id {trigger_id:d}"))
def watch_unknown_trigger(watch_context, financial_repository, trigger_id):
    watch_context.result = _watch(
        watch_context, financial_repository, trigger_ids=[trigger_id]
    )


@when("I stream an above-level quote then a below-level quote")
def stream_crossing_quotes(watch_context, financial_repository):
    et = ZoneInfo("America/New_York")
    quotes = [
        ("AAA", 110.0, 111.0, datetime(2022, 4, 4, 10, 0, tzinfo=et)),
        ("AAA", 105.0, 107.0, datetime(2022, 4, 4, 10, 1, tzinfo=et)),
        ("AAA", 104.0, 105.0, datetime(2022, 4, 4, 10, 2, tzinfo=et)),
    ]
    if watch_context.trigger_id is not None:
        watch_context.result = _watch(
            watch_context,
            financial_repository,
            scripted_quotes=quotes,
            trigger_ids=[watch_context.trigger_id],
        )
    else:
        watch_context.result = _watch(
            watch_context,
            financial_repository,
            scripted_quotes=quotes,
            symbols=["AAA"],
        )


@when("I watch with no selection and interrupt the stream")
def watch_interrupted(watch_context, financial_repository):
    watch_context.result = _watch(
        watch_context, financial_repository, interrupt_stream=True
    )


@then("the command succeeds")
def command_succeeds(watch_context):
    assert_that(watch_context.cli_result.exit_code, equal_to(0))


@then("the output is:")
def cli_output_is_exactly(watch_context, docstring):
    assert_that(watch_context.cli_result.output, equal_to(f"{docstring}\n"))


@then("the watch succeeds")
def watch_succeeds(watch_context):
    assert_that(watch_context.result.is_success(), equal_to(True))


@then("the watch errors are:")
def watch_errors_are_exactly(watch_context, docstring):
    assert_that(watch_context.result.is_success(), equal_to(False))
    assert_that(list(watch_context.result.errors), equal_to(docstring.splitlines()))


@then("the emitted lines are:")
def emitted_lines_are_exactly(watch_context, docstring):
    assert_that(watch_context.emitted, equal_to(docstring.splitlines()))


@then(parsers.parse('the price source receives symbols "{symbols}"'))
def price_source_receives_symbols(watch_context, symbols):
    assert watch_context.streamed is not None
    actual_symbols, _feed = watch_context.streamed
    assert_that(actual_symbols, equal_to(symbols.split()))


@then("the stored trigger is disabled")
def stored_trigger_is_disabled(watch_context, financial_repository):
    enabled_ids = {
        trigger.id for trigger in financial_repository.list_triggers(enabled_only=True)
    }
    assert watch_context.trigger_id not in enabled_ids, watch_context.emitted


# Signal handling (blocking child process, real SIGINT).


def _readline_timeout(proc, timeout: float) -> str:
    assert proc.stdout is not None
    ready, _, _ = select.select([proc.stdout], [], [], timeout)
    assert ready, "child produced no output in time"
    return proc.stdout.readline()


@given("a blocking watch is running in a child process")
def blocking_watch_running(watch_context):
    if os.name != "posix":
        pytest.skip("POSIX signals")
    proc = subprocess.Popen(
        [sys.executable, str(DRIVER)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(ROOT),
    )
    watch_context.proc = proc
    first = _readline_timeout(proc, timeout=30)
    assert "Watching 1 symbols" in first, f"child never reached the stream: {first!r}"
    watch_context.child_output = first


@when("I send SIGINT to the child process")
def send_sigint_to_child(watch_context):
    proc = watch_context.proc
    proc.send_signal(signal.SIGINT)
    rest, _ = proc.communicate(timeout=30)
    watch_context.child_output += rest


@then(parsers.parse("the child exits with code {code:d}"))
def child_exits_with_code(watch_context, code):
    assert watch_context.proc is not None
    assert_that(watch_context.proc.returncode, equal_to(code))


@then("the child output is:")
def child_output_is_exactly(watch_context, docstring):
    assert_that(watch_context.child_output, equal_to(f"{docstring}\n"))
