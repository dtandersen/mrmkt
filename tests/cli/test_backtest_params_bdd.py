from datetime import date
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command import _shared as shared
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "backtest_params.feature"
scenarios(str(FEATURE))


@pytest.fixture
def backtest_params_context(monkeypatch):
    context = SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
    )
    monkeypatch.setattr(
        shared,
        "create_local_ticker_repository",
        lambda: (context.local, lambda: None),
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the local ticker catalog contains these symbols:")
def local_ticker_catalog_contains_symbols(backtest_params_context, datatable):
    for row in _table_rows(datatable):
        backtest_params_context.local.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given("the local price catalog contains these daily bars:")
def local_price_catalog_contains_bars(backtest_params_context, datatable):
    for row in _table_rows(datatable):
        backtest_params_context.local.add_price(
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
    backtest_params_context.result = CliRunner().invoke(cli.app, args[1:])


@then("the command succeeds")
def backtest_command_succeeds(backtest_params_context):
    assert backtest_params_context.result.exit_code == 0, backtest_params_context.result.output


@then("the command fails")
def backtest_command_fails(backtest_params_context):
    assert backtest_params_context.result.exit_code != 0


@then(parsers.parse('the output mentions "{text}"'))
def backtest_output_mentions(backtest_params_context, text):
    output = backtest_params_context.result.output
    stderr = getattr(backtest_params_context.result, "stderr", "") or ""
    assert text in output or text in stderr, output
