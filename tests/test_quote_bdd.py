"""BDD coverage for the latest stock-quote command and CLI."""

from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    is_,
    not_,
    not_none,
)
from pytest_bdd import given, parsers, scenarios, then, when
from tests.fakes import FakeAlpacaDataClient
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.command.get_quote import GetQuote, GetQuoteRequest
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.ext.alpaca_quote import AlpacaQuoteGateway

scenarios("features/cli/quote.feature", "features/command/get_quote.feature")


@pytest.fixture
def quote_context():
    return SimpleNamespace(result=None, cli_result=None, failed=False, error="")


@pytest.fixture
def quote_data_client():
    return FakeAlpacaDataClient()


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


def _deps(financial_repository, alpaca_client, quote_data_client):
    return cli_dependencies_for_testing(
        repository=financial_repository,
        alpaca_client=alpaca_client,
        alpaca_data_client=quote_data_client,
    )


@given("the data feed quotes:")
def data_feed_quotes(datatable, quote_data_client):
    quote_data_client.set_quotes(_table_rows(datatable))


@given("the data feed has no quotes")
def data_feed_has_no_quotes(quote_data_client):
    quote_data_client.set_quotes([])


@given("the data feed request fails")
def data_feed_request_fails(quote_data_client):
    quote_data_client.error = RuntimeError("paper data unavailable")


@when(parsers.parse('I execute "{command}"'))
def execute_quote_command(
    quote_context, command, financial_repository, alpaca_client, quote_data_client
):
    args = split(command)
    quote_context.result = None
    quote_context.cli_result = CliRunner().invoke(
        cli.app,
        args[1:],
        obj=_deps(financial_repository, alpaca_client, quote_data_client),
    )


@when(parsers.parse('I get the quote for "{symbol}"'))
def get_quote_for_symbol(quote_context, symbol, quote_data_client):
    result = GetQuote(AlpacaQuoteGateway(quote_data_client)).execute(
        GetQuoteRequest(symbol=symbol)
    )
    quote_context.result = result
    quote_context.cli_result = None
    quote_context.failed = not result.is_success()
    quote_context.error = "; ".join(result.errors)


@then("the command succeeds")
def command_succeeds(quote_context):
    if quote_context.cli_result is not None:
        assert_that(quote_context.cli_result.exit_code, equal_to(0))
    else:
        assert_that(quote_context.failed, is_(False), quote_context.error)


@then("the command fails")
def command_fails(quote_context):
    if quote_context.cli_result is not None:
        assert_that(quote_context.cli_result.exit_code, not_(equal_to(0)))
    else:
        assert_that(quote_context.failed, is_(True))


@then("the quote command fails")
def quote_command_fails(quote_context):
    assert_that(quote_context.failed, is_(True))


@then("the console displays:")
def console_displays_exactly(quote_context, docstring):
    assert_that(quote_context.cli_result, not_none())
    assert_that(quote_context.cli_result.output, equal_to(f"{docstring}\n"))


@then(parsers.parse('the output reports "{message}"'))
def output_reports(quote_context, message):
    assert_that(quote_context.cli_result, not_none())
    assert_that(quote_context.cli_result.output, contains_string(message))


@then(parsers.parse('the quoted price is bid {bid} ask {ask} for "{symbol}"'))
def quoted_price_matches(quote_context, bid, ask, symbol):
    quote = quote_context.result.result
    assert_that(quote.symbol, equal_to(symbol))
    assert_that(quote.bid, equal_to(float(bid)))
    assert_that(quote.ask, equal_to(float(ask)))
