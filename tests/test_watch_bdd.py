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
from mrmkt.entity.trigger import DEFAULT_MESSAGE_TEMPLATE, Trigger

scenarios(
    "features/cli/watch.feature",
    "features/command/watch.feature",
)

ROOT = Path(__file__).parent.parent
DRIVER = Path(__file__).parent / "watch_blocking_driver.py"


@pytest.fixture
def watch_context(financial_repository):
    clock = ClockStub()
    clock.set_time(date(2022, 4, 1))
    context = SimpleNamespace(result=None)
    context.cli_result = None
    context.clock = clock
    context.emitted = []
    context.trigger_id = None
    context.proc = None
    context.child_output = ""
    context.quotes = None

    class CliPriceSource:
        def subscribe(self, symbols, feed, *, on_quote) -> None:
            pass

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


def _ensure_ticker(local, symbol, exchange="NASDAQ") -> None:
    if symbol not in {ticker.ticker for ticker in local.get_tickers()}:
        local.add_ticker(Ticker(ticker=symbol, exchange=exchange, type="us_equity"))


def _add_trigger(
    repository,
    name: str,
    symbol: str,
    frequency: str = "once_per_rearm",
    operator: str = "crossing-down",
    value: float | None = None,
    indicator: str = "risk-range",
    expires_at: date | None = None,
    message: str = DEFAULT_MESSAGE_TEMPLATE,
    enabled: bool = True,
):
    return repository.add_trigger(
        Trigger(
            id=None,
            name=name,
            symbol=symbol,
            indicator=indicator,
            operator=operator,
            frequency=frequency,
            value=value,
            expires_at=expires_at,
            message=message,
            enabled=enabled,
        )
    )


@given("the alerts catalog contains these symbols:")
def alerts_catalog_contains_symbols(watch_context, datatable, financial_repository):
    import contextlib

    from mrmkt.common.sql import Duplicate

    for row in _table_rows(datatable):
        with contextlib.suppress(Duplicate):
            financial_repository.add_ticker(
                Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
            )


@given(
    parsers.parse(
        "the daily price history of {symbol} from {start} to {end} rising {drift} per day"
    )
)
def daily_price_history(financial_repository, symbol, start, end, drift):
    drift = float(drift)
    day = date.fromisoformat(start)
    last = date.fromisoformat(end)
    bars = 0
    while day <= last:
        if day.weekday() < 5:
            close = round(100.0 + drift * bars, 2)
            _ensure_ticker(financial_repository, symbol)
            financial_repository.add_price(
                StockPrice(
                    symbol=symbol,
                    date=day,
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=1000.0,
                )
            )
            bars += 1
        day += timedelta(days=1)


@given("the stored triggers:")
def stored_triggers(watch_context, financial_repository, datatable):
    for row in _table_rows(datatable):
        trigger = _add_trigger(
            financial_repository,
            row["name"],
            row["symbol"],
            frequency=row.get("frequency") or "once_per_rearm",
            operator=row.get("operator") or "crossing-down",
            value=float(row["value"]) if row.get("value") else None,
            indicator=row.get("indicator") or "risk-range",
            expires_at=date.fromisoformat(row["expires_at"])
            if row.get("expires_at")
            else None,
            message=row.get("message") or DEFAULT_MESSAGE_TEMPLATE,
            enabled=(row.get("enabled") or "true").strip().lower() != "false",
        )
        watch_context.trigger_id = trigger.id


@given("the real time quotes:")
def realtime_quotes(watch_context, datatable):
    watch_context.quotes = [
        (
            row["symbol"],
            float(row["bid"]),
            float(row["ask"]),
            datetime.fromisoformat(row["timestamp"]),
        )
        for row in _table_rows(datatable)
    ]


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
    if scripted_quotes is None:
        scripted_quotes = watch_context.quotes or []

    class FakePriceSource:
        """Test source that emits scripted quotes."""

        def subscribe(self, symbols, feed, *, on_quote) -> None:
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


@when("I stream these quotes:")
def stream_quotes(watch_context, financial_repository, datatable):
    quotes = [
        (
            row["symbol"],
            float(row["bid"]),
            float(row["ask"]),
            datetime.fromisoformat(row["timestamp"]),
        )
        for row in _table_rows(datatable)
    ]
    if watch_context.trigger_id is not None:
        watch_context.result = _watch(
            watch_context,
            financial_repository,
            scripted_quotes=quotes,
            trigger_ids=[watch_context.trigger_id],
        )
    else:
        symbols = sorted({symbol for symbol, _bid, _ask, _ts in quotes})
        watch_context.result = _watch(
            watch_context,
            financial_repository,
            scripted_quotes=quotes,
            symbols=symbols,
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
