from datetime import date
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, equal_to, not_
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.common.clock import ClockStub
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "list_prices.feature"
scenarios(str(FEATURE))


@pytest.fixture
def price_list_context(financial_repository):
    clock = ClockStub()
    clock.set_time(date(2024, 1, 31))
    context = SimpleNamespace(
        clock=clock,
        result=None,
    )
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        clock=context.clock,
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


def _make_price(row):
    return StockPrice(
        symbol=row["symbol"],
        date=date.fromisoformat(row["date"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )


@given("the local price catalog contains these daily bars:")
def seed_price_list_catalog(price_list_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_price(_make_price(row))


@given(parsers.parse('the fake clock says today is "{today}"'))
def fake_clock_says_today(price_list_context, today):
    price_list_context.clock.set_time(date.fromisoformat(today))


@when(parsers.parse('I execute "{command}"'))
def execute_list_prices_command(price_list_context, command):
    args = split(command)
    price_list_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=price_list_context.deps
    )


@then("the command succeeds")
def list_prices_command_succeeds(price_list_context):
    assert_that(price_list_context.result.exit_code, equal_to(0))


@then("the command fails")
def list_prices_command_fails(price_list_context):
    assert_that(price_list_context.result.exit_code, not_(equal_to(0)))


@then("the price table lists these rows in order:")
def price_table_lists_rows(price_list_context, datatable):
    expected = [
        f"{row['symbol']} | {row['date']} | {float(row['open']):g} | "
        f"{float(row['high']):g} | {float(row['low']):g} | "
        f"{float(row['close']):g} | {float(row['volume']):g}"
        for row in _table_rows(datatable)
    ]
    actual = [
        line
        for line in price_list_context.result.output.splitlines()
        if " | " in line and not line.startswith("SYMBOL |")
    ]
    assert_that(actual, equal_to(expected))


@then("the output says no prices were found")
def output_says_no_prices(price_list_context):
    assert_that(price_list_context.result.output.strip(), equal_to("No prices found."))
