"""BDD coverage for watch CLI commands and the WatchPrices command."""

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
from mrmkt.command.create_trigger import CreateTrigger, CreateTriggerRequest
from mrmkt.command.watch import WatchPrices, WatchPricesRequest
from mrmkt.common.clock import ClockStub
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

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
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
    )
    yield context
    proc = context.proc
    if proc is not None and proc.poll() is None:
        proc.kill()
        proc.wait()


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


def _business_days(start: date, n: int) -> list:
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


def _add_climb(local, symbol, dip: bool, tag: str | None = None) -> None:
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
    if tag is not None:
        local.add_tag(symbol, "NASDAQ", tag)


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


# Shared catalog givens (CLI level).


@given("the alerts catalog contains these symbols:")
def alerts_catalog_contains_symbols(watch_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse("each alerts symbol has a 60-bar climb with a dip tagged {tag}"))
def alerts_symbols_have_climb_with_dip(watch_context, tag, financial_repository):
    for ticker in financial_repository.get_tickers():
        _add_climb(financial_repository, ticker.ticker, dip=True, tag=tag)


@given(parsers.parse("{symbol} has a 60-bar climb with a dip"))
def symbol_has_dip(watch_context, symbol, financial_repository):
    _add_climb(financial_repository, symbol, dip=True)


@given(parsers.parse("{symbol} has a 60-bar steady climb"))
def symbol_has_steady_climb(watch_context, symbol, financial_repository):
    _add_climb(financial_repository, symbol, dip=False)


@given(parsers.parse("{symbol} has a 5-bar climb"))
def symbol_has_short_climb(watch_context, symbol, financial_repository):
    _add_short_climb(financial_repository, symbol)


@given(parsers.parse('stored trigger "{name}" watches "{symbol}" crossing down'))
def stored_trigger_watches_symbol(watch_context, name, symbol, financial_repository):
    result = CreateTrigger(financial_repository).execute(
        CreateTriggerRequest(
            name=name, symbol=symbol, indicator="risk-range", operator="crossing-down"
        )
    )
    assert_that(result.is_success(), equal_to(True))
    assert result.result is not None
    watch_context.trigger_id = result.result.id


# CLI level.


@when(parsers.parse('I execute "{command}"'))
def execute_watch_command(watch_context, command):
    args = split(command)
    watch_context.cli_result = CliRunner().invoke(
        cli.app, args[1:], obj=watch_context.deps
    )


# Command level.


def _watch(
    watch_context,
    financial_repository,
    interrupt_stream=False,
    scripted_ticks=None,
    sink_factory=None,
    **kwargs,
):
    from mrmkt.command.ranges import ListRanges
    from mrmkt.command.watch import PriceTick
    from mrmkt.composition import build_watch_sinks

    def emit(line: str, err: bool = False) -> None:
        watch_context.emitted.append(line)

    class FakePriceSource:
        """Test PriceSource: records subscriptions, replays scripted ticks."""

        def subscribe(self, symbols, feed, *, on_trade, on_bar) -> None:
            if interrupt_stream:
                raise KeyboardInterrupt
            if scripted_ticks is not None:
                for symbol, price, moment in scripted_ticks:
                    on_trade(PriceTick(symbol=symbol, price=price, moment=moment))
            else:
                watch_context.streamed = (list(symbols), feed)

    command = WatchPrices(
        financial_repository,
        watch_context.clock,
        FakePriceSource(),
        emit,
        ranges=ListRanges(financial_repository, watch_context.clock),
        sink_factory=sink_factory or build_watch_sinks,
    )
    return command.execute(WatchPricesRequest(**kwargs))


@when("I watch with no selection in dry-run mode")
def watch_bare_dry_run(watch_context, financial_repository):
    watch_context.result = _watch(watch_context, financial_repository, dry_run=True)


@when("I watch with no selection in live mode")
def watch_bare_live(watch_context, financial_repository):
    watch_context.result = _watch(watch_context, financial_repository, dry_run=False)


@when("I watch with no selection and interrupt the stream")
def watch_bare_interrupted(watch_context, financial_repository):
    watch_context.result = _watch(
        watch_context, financial_repository, dry_run=False, interrupt_stream=True
    )


@when("I stream an above-level tick then a below-level tick in live mode")
def stream_crossing_ticks(watch_context, financial_repository):
    from mrmkt.command.alerts import ListSink

    et = ZoneInfo("America/New_York")
    ticks = [
        ("AAA", 1e6, datetime(2022, 4, 4, 10, 0, tzinfo=et)),
        ("AAA", 1e-6, datetime(2022, 4, 4, 10, 1, tzinfo=et)),
    ]
    recorder = ListSink()
    watch_context.recorded = recorder
    watch_context.result = _watch(
        watch_context,
        financial_repository,
        symbols=["AAA"],
        dry_run=False,
        scripted_ticks=ticks,
        sink_factory=lambda names: recorder,
    )


@when(parsers.parse('I watch symbols "{first}" and "{second}" in dry-run mode'))
def watch_two_symbols_dry_run(watch_context, first, second, financial_repository):
    watch_context.result = _watch(
        watch_context, financial_repository, symbols=[first, second], dry_run=True
    )


@when(
    parsers.parse('I watch symbol "{symbol}" plus its stored trigger in dry-run mode')
)
def watch_symbol_plus_trigger_dry_run(watch_context, symbol, financial_repository):
    watch_context.result = _watch(
        watch_context,
        financial_repository,
        symbols=[symbol],
        trigger_ids=[watch_context.trigger_id],
        dry_run=True,
    )


@when(parsers.parse("I watch trigger id {trigger_id:d} in dry-run mode"))
def watch_unknown_trigger_dry_run(watch_context, trigger_id, financial_repository):
    watch_context.result = _watch(
        watch_context, financial_repository, trigger_ids=[trigger_id], dry_run=True
    )


@when(
    parsers.parse(
        'I watch symbol "{symbol}" with session policy "{policy}" in dry-run mode'
    )
)
def watch_bad_session_policy(watch_context, symbol, policy, financial_repository):
    watch_context.result = _watch(
        watch_context,
        financial_repository,
        symbols=[symbol],
        session_policy=policy,
        dry_run=True,
    )


@when(parsers.parse('I watch symbol "{symbol}" with sink "{sink}" in dry-run mode'))
def watch_bad_sink(watch_context, symbol, sink, financial_repository):
    watch_context.result = _watch(
        watch_context,
        financial_repository,
        symbols=[symbol],
        sinks=[sink],
        dry_run=True,
    )


@when(
    parsers.parse(
        'I watch symbol "{symbol}" with indicator "{indicator}" in dry-run mode'
    )
)
def watch_bad_indicator(watch_context, symbol, indicator, financial_repository):
    watch_context.result = _watch(
        watch_context,
        financial_repository,
        symbols=[symbol],
        indicator=indicator,
        dry_run=True,
    )


# Shared outcomes.


@then("the command succeeds")
def command_succeeds(watch_context):
    if watch_context.cli_result is not None:
        assert_that(watch_context.cli_result.exit_code, equal_to(0))
    else:
        assert_that(watch_context.result.is_success(), equal_to(True))


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


@then(parsers.parse('the stream runner receives symbols "{symbol}"'))
def stream_runner_receives_symbols(watch_context, symbol):
    assert watch_context.streamed is not None
    symbols, _feed = watch_context.streamed
    assert_that(symbols, equal_to([symbol]))


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


@then("the recorded alert lines are:")
def recorded_alert_lines_are_exactly(watch_context, docstring):
    from mrmkt.command.alerts import format_alert

    lines = [format_alert(alert) for alert in watch_context.recorded.alerts]
    assert_that(lines, equal_to(docstring.splitlines()))
