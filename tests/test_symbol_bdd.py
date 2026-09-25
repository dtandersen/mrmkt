"""BDD coverage for symbol commands and CLI commands."""

from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_item,
    has_length,
    is_,
    not_,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.list_symbols import ListSymbols
from mrmkt.command.base import BaseResult
from mrmkt.command.import_symbols import ImportSymbols, ImportSymbolsRequest
from mrmkt.command.symbols_label import LabelSymbols
from mrmkt.command.symbols_unlabel import UnlabelSymbols
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker

scenarios(
    "features/cli/list_symbols.feature",
    "features/cli/import_stock_symbols.feature",
    "features/cli/symbol_tags.feature",
    "features/command/list_symbols.feature",
    "features/command/import_symbols.feature",
    "features/command/symbol_tags.feature",
)


class UnavailableTickerRepository:
    def get_tickers(self):
        raise RuntimeError("ticker catalog unavailable")


@pytest.fixture
def symbol_context():
    return SimpleNamespace(
        result=None,
        cli_result=None,
        failed=False,
        error="",
        catalog_unreadable=False,
    )


@pytest.fixture
def remote_repository() -> InMemoryFinancialRepository:
    """Provide a fresh in-memory repository acting as the remote symbol catalog."""
    return InMemoryFinancialRepository()


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("Alpaca returns these assets:")
def alpaca_returns_assets(alpaca_client, datatable):
    alpaca_client.set_assets(_table_rows(datatable))


def _deps(symbol_context, financial_repository, alpaca_client):
    repository = (
        UnavailableTickerRepository()
        if symbol_context.catalog_unreadable
        else financial_repository
    )
    return cli_dependencies_for_testing(
        repository=repository,
        alpaca_client=alpaca_client,
    )


def _invoke_cli(symbol_context, financial_repository, alpaca_client, args):
    symbol_context.result = None
    symbol_context.cli_result = CliRunner().invoke(
        cli.app, args, obj=_deps(symbol_context, financial_repository, alpaca_client)
    )


def _invoke_command(symbol_context, command, *args, **kwargs):
    symbol_context.result = None
    symbol_context.cli_result = None
    symbol_context.failed = False
    symbol_context.error = ""
    try:
        symbol_context.result = command.execute(*args, **kwargs)
    except ValueError as error:
        symbol_context.failed = True
        symbol_context.error = str(error)
    if (
        isinstance(symbol_context.result, BaseResult)
        and not symbol_context.result.success
    ):
        symbol_context.failed = True
        symbol_context.error = "; ".join(symbol_context.result.errors)


@given("the local ticker catalog contains these symbols:")
def local_catalog_contains_symbols(datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given("the local ticker catalog is empty")
def local_catalog_is_empty(financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@given("the local ticker catalog cannot be read")
def local_catalog_cannot_be_read(symbol_context):
    symbol_context.catalog_unreadable = True


@given("the local ticker catalog already contains:")
def local_ticker_catalog_already_contains(datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type="us_equity")
        )


@given("Alpaca returns no assets")
def alpaca_returns_no_assets(alpaca_client):
    alpaca_client.assets = []


@given("the Alpaca asset request fails")
def alpaca_asset_request_fails(alpaca_client):
    alpaca_client.error = RuntimeError("Alpaca request unavailable")


@given(parsers.parse('ticker "{symbol}" on "{exchange}" already has tag "{tag}"'))
def ticker_already_has_tag(symbol_context, symbol, exchange, tag, financial_repository):
    financial_repository.add_tag(symbol, exchange, tag)


@given("the remote symbol catalog contains:")
def remote_catalog_contains(remote_repository, datatable):
    for row in _table_rows(datatable):
        remote_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@when('I run "mrmkt symbols list"')
def run_list_symbols(symbol_context, financial_repository, alpaca_client):
    _invoke_cli(
        symbol_context, financial_repository, alpaca_client, ["symbols", "list"]
    )


@when('I run "mrmkt symbols import --provider alpaca"')
def run_symbol_import(symbol_context, financial_repository, alpaca_client):
    _invoke_cli(
        symbol_context,
        financial_repository,
        alpaca_client,
        ["symbols", "import", "--provider", "alpaca"],
    )


@when(parsers.parse('I execute "{command}"'))
def execute_symbol_command(
    symbol_context, command, financial_repository, alpaca_client
):
    args = split(command)
    _invoke_cli(symbol_context, financial_repository, alpaca_client, args[1:])


@when("I list stored symbols")
def list_stored_symbols(symbol_context, financial_repository):
    _invoke_command(symbol_context, ListSymbols(financial_repository))


@when(parsers.parse('I list stored symbols tagged "{tag}"'))
def list_stored_symbols_by_tag(symbol_context, tag, financial_repository):
    _invoke_command(symbol_context, ListSymbols(financial_repository), tag=tag)


@when(parsers.parse('I import symbols from "{provider}"'))
def import_symbols_command(
    symbol_context, provider, financial_repository, remote_repository
):
    _invoke_command(
        symbol_context,
        ImportSymbols(remote_repository, financial_repository),
        ImportSymbolsRequest(provider=provider),
    )


@when(parsers.parse('I label "{symbols}" with "{tag}"'))
def label_symbols_command(symbol_context, symbols, tag, financial_repository):
    _invoke_command(
        symbol_context,
        LabelSymbols(financial_repository),
        symbols=symbols,
        tag=tag,
    )


@when(parsers.parse('I label nothing with "{tag}"'))
def label_no_symbols_command(symbol_context, tag, financial_repository):
    _invoke_command(
        symbol_context,
        LabelSymbols(financial_repository),
        symbols="",
        tag=tag,
    )


@when(parsers.parse('I remove tag "{tag}" from "{symbols}"'))
def unlabel_symbols_command(symbol_context, tag, symbols, financial_repository):
    _invoke_command(
        symbol_context,
        UnlabelSymbols(financial_repository),
        symbols=symbols,
        tag=tag,
    )


@then("the command succeeds")
def command_succeeds(symbol_context):
    if symbol_context.cli_result is not None:
        assert_that(symbol_context.cli_result.exit_code, equal_to(0))
    else:
        assert_that(symbol_context.failed, is_(False), symbol_context.error)


@then("the command fails")
def command_fails(symbol_context):
    assert_that(symbol_context.cli_result.exit_code, not_(equal_to(0)))


@then("the command fails with errors:")
def command_fails_with_errors(symbol_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "message"]))
    assert_that(symbol_context.failed, equal_to(True), "expected the command to fail")
    for row in datatable[1:]:
        field, message = str(row[0]), str(row[1])
        assert_that(symbol_context.error, contains_string(field))
        assert_that(symbol_context.error, contains_string(message))


@then("the symbol table lists these rows in order:")
def symbol_table_lists_rows(symbol_context, datatable):
    expected = [
        f"{row['symbol']} | {row['exchange']} | {row['type']}"
        for row in _table_rows(datatable)
    ]
    actual = [
        line
        for line in symbol_context.cli_result.output.splitlines()
        if " | " in line and not line.startswith("SYMBOL |")
    ]
    assert_that(actual, equal_to(expected))


@then("the output says no symbols were found")
def output_says_no_symbols(symbol_context):
    assert_that(symbol_context.cli_result.output.strip(), equal_to("No symbols found."))


@then("the output reports that listing symbols failed")
def output_reports_listing_failure(symbol_context):
    assert_that(
        symbol_context.cli_result.output, contains_string("Failed to list symbols")
    )


@then("the local ticker catalog contains:")
def local_ticker_catalog_contains(symbol_context, datatable, financial_repository):
    expected = {
        (row["symbol"], row["exchange"], row["type"]) for row in _table_rows(datatable)
    }
    actual = {
        (ticker.ticker, ticker.exchange, ticker.type)
        for ticker in financial_repository.get_tickers()
    }
    assert_that(actual, equal_to(expected))


@then(
    parsers.parse(
        'the local ticker catalog contains exactly one "{symbol}" on "{exchange}"'
    )
)
def ticker_is_present_once(symbol_context, symbol, exchange, financial_repository):
    matches = [
        ticker
        for ticker in financial_repository.get_tickers()
        if ticker.ticker == symbol and ticker.exchange == exchange
    ]
    assert_that(matches, has_length(1))


@then(parsers.re(r"the import reports (?P<count>\d+) newly imported symbols?"))
def import_reports_new_symbol_count(symbol_context, count):
    assert_that(symbol_context.cli_result.exit_code, equal_to(0))
    assert_that(
        symbol_context.cli_result.output,
        contains_string(f"Imported {count} newly imported symbol"),
    )


@then("the local ticker catalog remains empty")
def local_ticker_catalog_remains_empty(symbol_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@then("no symbols are added to the local ticker catalog")
def no_symbols_added_after_failure(symbol_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@then("the import reports a failure")
def import_reports_failure(symbol_context):
    assert_that(symbol_context.cli_result.exit_code, not_(equal_to(0)))
    assert_that(
        symbol_context.cli_result.output,
        contains_string("Failed to import symbols from Alpaca"),
    )


@then(parsers.parse('ticker "{symbol}" on "{exchange}" has tag "{tag}"'))
def ticker_has_tag(symbol_context, symbol, exchange, tag, financial_repository):
    assert_that(financial_repository.get_tags(symbol, exchange), has_item(tag))


@then(parsers.parse('ticker "{symbol}" on "{exchange}" has no tags'))
def ticker_has_no_tags(symbol_context, symbol, exchange, financial_repository):
    assert_that(financial_repository.get_tags(symbol, exchange), equal_to([]))


@then("the symbol list contains:")
def filtered_symbol_list_contains(symbol_context, datatable):
    expected = {(row["symbol"], row["exchange"]) for row in _table_rows(datatable)}
    lines = symbol_context.cli_result.output.splitlines()[1:]
    actual = {
        tuple(part.strip() for part in line.split("|")[:2])
        for line in lines
        if "|" in line
    }
    assert_that(actual, equal_to(expected))


@then("the output reports 0 new tag assignments")
def output_reports_no_new_assignments(symbol_context):
    assert_that(
        symbol_context.cli_result.output,
        contains_string("Added 0 'sp500' tag assignments"),
    )


@then("the output reports 2 tag assignments")
def output_reports_two_assignments(symbol_context):
    assert_that(
        symbol_context.cli_result.output,
        contains_string("Added 2 'sp500' tag assignments"),
    )


@then("the stored symbols are:")
def stored_symbols_are(symbol_context, datatable):
    expected = [
        (row["symbol"], row["exchange"], row["type"]) for row in _table_rows(datatable)
    ]
    actual = [
        (ticker.ticker, ticker.exchange, ticker.type)
        for ticker in symbol_context.result
    ]
    assert_that(actual, equal_to(expected))


@then("no stored symbols are listed")
def no_stored_symbols_listed(symbol_context):
    assert_that(symbol_context.result, equal_to([]))


@then(parsers.parse("the import count is {count:d}"))
def import_count_is(symbol_context, count):
    assert_that(symbol_context.result.imported_count, equal_to(count))


@then("the tag change is:")
def tag_change_is(symbol_context, datatable):
    headers = [str(header) for header in datatable[0]]
    assert_that(headers, equal_to(["field", "value"]))
    expected = {str(row[0]): str(row[1]) for row in datatable[1:]}
    actual = {
        "changed": str(symbol_context.result.changed_count),
        "matched": str(symbol_context.result.matched_count),
        "unmatched": str(symbol_context.result.unmatched_count),
        "tag": symbol_context.result.tag,
    }
    for field, value in expected.items():
        assert_that(actual[field], equal_to(value))
