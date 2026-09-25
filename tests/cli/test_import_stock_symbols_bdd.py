from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, has_length, not_
from alpaca.trading.enums import AssetClass, AssetStatus
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "import_stock_symbols.feature"
scenarios(str(FEATURE))


class FakeAlpacaClient:
    def __init__(self):
        self.assets = []
        self.error = None

    def get_all_assets(self, filter=None):
        if self.error is not None:
            raise self.error
        return self.assets


@pytest.fixture
def symbol_import_context(financial_repository):
    context = SimpleNamespace(
        alpaca=FakeAlpacaClient(),
        result=None,
    )
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        alpaca_client=context.alpaca,
    )
    return context


def _table_rows(datatable):
    rows = datatable
    headers = [str(header) for header in rows[0]]
    return [dict(zip(headers, row, strict=True)) for row in rows[1:]]


def _set_alpaca_assets(context, rows):
    context.alpaca.assets = [
        SimpleNamespace(
            symbol=row["symbol"],
            exchange=row["exchange"],
            asset_class=AssetClass(row["asset_class"]),
            status=AssetStatus(row["status"]),
            tradable=row["tradable"].lower() == "true",
        )
        for row in rows
    ]


@given("Alpaca returns these assets:")
def alpaca_returns_assets(symbol_import_context, datatable):
    _set_alpaca_assets(symbol_import_context, _table_rows(datatable))


@given("the local ticker catalog is empty")
def local_ticker_catalog_is_empty(symbol_import_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@given("the local ticker catalog already contains:")
def local_ticker_catalog_already_contains(symbol_import_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type="us_equity")
        )


@given("Alpaca returns no assets")
def alpaca_returns_no_assets(symbol_import_context):
    symbol_import_context.alpaca.assets = []


@given("the Alpaca asset request fails")
def alpaca_asset_request_fails(symbol_import_context):
    symbol_import_context.alpaca.error = RuntimeError("Alpaca request unavailable")


@when('I run "mrmkt symbols import --provider alpaca"')
def run_symbol_import(symbol_import_context):
    symbol_import_context.result = CliRunner().invoke(
        cli.app,
        ["symbols", "import", "--provider", "alpaca"],
        obj=symbol_import_context.deps,
    )


@then("the command succeeds")
def command_succeeds(symbol_import_context):
    assert_that(symbol_import_context.result.exit_code, equal_to(0))


@then("the local ticker catalog contains:")
def local_ticker_catalog_contains(symbol_import_context, datatable, financial_repository):
    expected = {
        (row["symbol"], row["exchange"], row["type"])
        for row in _table_rows(datatable)
    }
    actual = {
        (ticker.ticker, ticker.exchange, ticker.type)
        for ticker in financial_repository.get_tickers()
    }
    assert_that(actual, equal_to(expected))


@then(parsers.parse('the local ticker catalog contains exactly one "{symbol}" on "{exchange}"'))
def ticker_is_present_once(symbol_import_context, symbol, exchange, financial_repository):
    matches = [
        ticker
        for ticker in financial_repository.get_tickers()
        if ticker.ticker == symbol and ticker.exchange == exchange
    ]
    assert_that(matches, has_length(1))


@then(parsers.re(r"the import reports (?P<count>\d+) newly imported symbols?"))
def import_reports_new_symbol_count(symbol_import_context, count):
    assert_that(symbol_import_context.result.exit_code, equal_to(0))
    assert_that(
        symbol_import_context.result.output,
        contains_string(f"Imported {count} newly imported symbol"),
    )


@then("the local ticker catalog remains empty")
def local_ticker_catalog_remains_empty(symbol_import_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@then("no symbols are added to the local ticker catalog")
def no_symbols_added_after_failure(symbol_import_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@then("the import reports a failure")
def import_reports_failure(symbol_import_context):
    assert_that(symbol_import_context.result.exit_code, not_(equal_to(0)))
    assert_that(
        symbol_import_context.result.output,
        contains_string("Failed to import symbols from Alpaca"),
    )
