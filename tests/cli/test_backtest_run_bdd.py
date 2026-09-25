"""BDD coverage for `backtest run` benchmark plumbing and new strategies."""

from datetime import date, timedelta
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, has_item, has_length
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "backtest_run.feature"
scenarios(str(FEATURE))

N_BARS = 400
START = date(2022, 1, 3)


@pytest.fixture
def backtest_run_context(financial_repository):
    context = SimpleNamespace(result=None)
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
    )
    return context


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


def _add_bars(local, symbol: str, closes: list) -> None:
    for day, close in zip(_business_days(START, len(closes)), closes, strict=True):
        local.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=close,
                high=close * 1.005,
                low=close * 0.995,
                close=close,
                volume=1000.0,
            )
        )


@given("the local ticker catalog contains these symbols:")
def local_ticker_catalog_contains_symbols(backtest_run_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse("the local price catalog contains a 400-bar climb with a dip for {symbol}"))
def price_catalog_contains_climb_with_dip(backtest_run_context, symbol, financial_repository):
    closes = [100.0 * (1.002**i) for i in range(N_BARS)]
    for pos, factor in ((350, 0.95), (351, 0.96), (352, 0.98)):
        closes[pos] *= factor
    _add_bars(financial_repository, symbol, closes)


@given(parsers.parse("the local price catalog contains a 400-bar steady climb for {symbol}"))
def price_catalog_contains_steady_climb(backtest_run_context, symbol, financial_repository):
    _add_bars(financial_repository, symbol, [400.0 * (1.001**i) for i in range(N_BARS)])


@given(parsers.parse("the local price catalog contains a 400-bar rise-then-fall for {symbol}"))
def price_catalog_contains_rise_then_fall(backtest_run_context, symbol, financial_repository):
    # Flat start so the fast/slow cross-up is a real transition, then a
    # climb and a fall for a complete round trip inside the window.
    flat = [100.0] * 30
    peak = 100.0 * (1.002**170)
    closes = flat + [100.0 * (1.002**i) for i in range(1, 171)]
    closes += [peak * (0.9985**i) for i in range(1, 201)]
    assert_that(closes, has_length(N_BARS))
    _add_bars(financial_repository, symbol, closes)


@when(parsers.parse('I execute "{command}"'))
def execute_backtest_command(backtest_run_context, command):
    args = split(command)
    backtest_run_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=backtest_run_context.deps
    )


@then("the command succeeds")
def backtest_command_succeeds(backtest_run_context):
    assert_that(backtest_run_context.result.exit_code, equal_to(0))


@then(parsers.parse('the output mentions "{text}"'))
def backtest_output_mentions(backtest_run_context, text):
    output = backtest_run_context.result.output
    stderr = getattr(backtest_run_context.result, "stderr", "") or ""
    assert_that([output, stderr], has_item(contains_string(text)))
