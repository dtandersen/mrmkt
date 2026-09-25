from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "symbol_tags.feature"
scenarios(str(FEATURE))


@pytest.fixture
def symbol_tag_context():
    context = SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
    )
    context.deps = cli_dependencies_for_testing(
        repository_factory=lambda: (context.local, lambda: None),
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the local ticker catalog contains these symbols:")
def local_ticker_catalog_contains_symbols(symbol_tag_context, datatable):
    for row in _table_rows(datatable):
        symbol_tag_context.local.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse('ticker "{symbol}" on "{exchange}" already has tag "{tag}"'))
def ticker_already_has_tag(symbol_tag_context, symbol, exchange, tag):
    symbol_tag_context.local.add_tag(symbol, exchange, tag)


@when(parsers.parse('I execute "{command}"'))
def execute_symbol_tag_command(symbol_tag_context, command):
    args = split(command)
    symbol_tag_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=symbol_tag_context.deps
    )


@then("the command succeeds")
def symbol_tag_command_succeeds(symbol_tag_context):
    assert symbol_tag_context.result.exit_code == 0, symbol_tag_context.result.output


@then(parsers.parse('ticker "{symbol}" on "{exchange}" has tag "{tag}"'))
def ticker_has_tag(symbol_tag_context, symbol, exchange, tag):
    assert tag in symbol_tag_context.local.get_tags(symbol, exchange)


@then(parsers.parse('ticker "{symbol}" on "{exchange}" has no tags'))
def ticker_has_no_tags(symbol_tag_context, symbol, exchange):
    assert symbol_tag_context.local.get_tags(symbol, exchange) == []


@then("the symbol list contains:")
def filtered_symbol_list_contains(symbol_tag_context, datatable):
    expected = {
        (row["symbol"], row["exchange"])
        for row in _table_rows(datatable)
    }
    lines = symbol_tag_context.result.output.splitlines()[1:]
    actual = {
        tuple(part.strip() for part in line.split("|")[:2])
        for line in lines
        if "|" in line
    }
    assert actual == expected


@then("the output reports 0 new tag assignments")
def output_reports_no_new_assignments(symbol_tag_context):
    assert "Added 0 'sp500' tag assignments" in symbol_tag_context.result.output


@then("the output reports 2 tag assignments")
def output_reports_two_assignments(symbol_tag_context):
    assert "Added 2 'sp500' tag assignments" in symbol_tag_context.result.output
