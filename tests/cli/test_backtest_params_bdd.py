from datetime import date
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, has_item, not_
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "backtest_params.feature"
scenarios(str(FEATURE))


@pytest.fixture
def backtest_params_context(financial_repository):
    context = SimpleNamespace(result=None)
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the local ticker catalog contains these symbols:")
def local_ticker_catalog_contains_symbols(backtest_params_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given("the local price catalog contains these daily bars:")
def local_price_catalog_contains_bars(backtest_params_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_price(
            StockPrice(
                symbol=row["symbol"],
                date=date.fromisoformat(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )


@when(parsers.parse('I execute "{command}"'))
def execute_backtest_command(backtest_params_context, command):
    args = split(command)
    backtest_params_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=backtest_params_context.deps
    )


@then("the command succeeds")
def backtest_command_succeeds(backtest_params_context):
    assert_that(backtest_params_context.result.exit_code, equal_to(0))


@then("the command fails")
def backtest_command_fails(backtest_params_context):
    assert_that(backtest_params_context.result.exit_code, not_(equal_to(0)))


@then(parsers.parse('the output mentions "{text}"'))
def backtest_output_mentions(backtest_params_context, text):
    output = backtest_params_context.result.output
    stderr = getattr(backtest_params_context.result, "stderr", "") or ""
    assert_that([output, stderr], has_item(contains_string(text)))
