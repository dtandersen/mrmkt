from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, not_
from pytest_bdd import given, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "list_symbols.feature"
scenarios(str(FEATURE))


class UnavailableTickerRepository:
    def get_tickers(self):
        raise RuntimeError("ticker catalog unavailable")


@pytest.fixture
def symbol_list_context(financial_repository):
    context = SimpleNamespace(result=None)

    context.deps = cli_dependencies_for_testing(repository=financial_repository)
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the local ticker catalog contains these symbols:")
def local_catalog_contains_symbols(symbol_list_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given("the local ticker catalog is empty")
def local_catalog_is_empty(symbol_list_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@given("the local ticker catalog cannot be read")
def local_catalog_cannot_be_read(symbol_list_context):
    symbol_list_context.deps = cli_dependencies_for_testing(
        repository=UnavailableTickerRepository(),
    )


@when('I run "mrmkt symbols list"')
def run_list_symbols(symbol_list_context):
    symbol_list_context.result = CliRunner().invoke(
        cli.app, ["symbols", "list"], obj=symbol_list_context.deps
    )


@then("the command succeeds")
def list_command_succeeds(symbol_list_context):
    assert_that(symbol_list_context.result.exit_code, equal_to(0))


@then("the symbol table lists these rows in order:")
def symbol_table_lists_rows(symbol_list_context, datatable):
    expected = [
        f"{row['symbol']} | {row['exchange']} | {row['type']}"
        for row in _table_rows(datatable)
    ]
    actual = [
        line
        for line in symbol_list_context.result.output.splitlines()
        if " | " in line and not line.startswith("SYMBOL |")
    ]
    assert_that(actual, equal_to(expected))


@then("the output says no symbols were found")
def output_says_no_symbols(symbol_list_context):
    assert_that(symbol_list_context.result.output.strip(), equal_to("No symbols found."))


@then("the command fails")
def list_command_fails(symbol_list_context):
    assert_that(symbol_list_context.result.exit_code, not_(equal_to(0)))


@then("the output reports that listing symbols failed")
def output_reports_listing_failure(symbol_list_context):
    assert_that(symbol_list_context.result.output, contains_string("Failed to list symbols"))
