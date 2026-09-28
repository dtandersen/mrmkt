"""Thin CLI coverage for the fundamentals commands (argument passing)."""

import datetime
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, not_
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.common.clock import ClockStub
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.ext.tiingo_fundamentals import DailyMarketCap, SymbolFundamentals

scenarios(str(Path(__file__).parent.parent / "features" / "cli" / "fundamentals.feature"))


class FakeFundamentalsSource:
    def __init__(self):
        self.bundles = {}
        self.calls = []

    def get_fundamentals(self, symbols, end):
        self.calls.append((list(symbols), end))
        return {
            symbol: self.bundles[symbol]
            for symbol in symbols
            if symbol in self.bundles
        }


def _bundle(symbol, filing, caps):
    filing_date = datetime.date.fromisoformat(filing)
    return SymbolFundamentals(
        symbol=symbol,
        incomes=[
            IncomeStatement(
                symbol=symbol,
                date=filing_date,
                netIncome=1000000000.0,
                waso=1000,
                consolidated_net_income=1000000000.0,
            )
        ],
        balances=[
            BalanceSheet(
                symbol=symbol,
                date=filing_date,
                totalAssets=5000000000.0,
                totalLiabilities=2000000000.0,
            )
        ],
        cashflows=[
            CashFlow(
                symbol=symbol,
                date=filing_date,
                operating_cash_flow=800000000.0,
                capital_expenditure=-100000000.0,
                free_cash_flow=700000000.0,
                dividend_payments=-50000000.0,
            )
        ],
        shares_by_date={filing_date: 1000.0},
        daily_caps=[
            DailyMarketCap(
                date=datetime.date.fromisoformat(day), market_cap=float(cap)
            )
            for day, cap in (pair.split(":") for pair in caps.split(",") if pair)
        ],
    )


@pytest.fixture
def fundamentals_cli_context(financial_repository):
    clock = ClockStub()
    clock.set_time(datetime.date(2024, 4, 30))
    source = FakeFundamentalsSource()
    context = SimpleNamespace(source=source, result=None)
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        clock=clock,
        fundamentals_source=source,
    )
    return context


@given("stored bars:")
def stored_bars(fundamentals_cli_context, datatable, financial_repository):
    for row in datatable[1:]:
        financial_repository.add_price(
            StockPrice(
                symbol=row[0],
                date=datetime.date.fromisoformat(row[1]),
                open=float(row[2]),
                high=float(row[2]),
                low=float(row[2]),
                close=float(row[2]),
                volume=1000.0,
            )
        )


@given("the local ticker catalog contains these symbols:")
def local_catalog(fundamentals_cli_context, datatable, financial_repository):
    for row in datatable[1:]:
        financial_repository.add_ticker(
            Ticker(ticker=row[0], exchange=row[1], type=row[2])
        )


@given(parsers.parse('ticker "{symbol}" on "{exchange}" already has tag "{tag}"'))
def already_tagged(fundamentals_cli_context, symbol, exchange, tag, financial_repository):
    financial_repository.add_tag(symbol, exchange, tag)


@given(
    parsers.parse(
        'the fundamentals source serves "{symbol}" with filing "{filing}" and caps "{caps}"'
    )
)
def source_serves(fundamentals_cli_context, symbol, filing, caps):
    fundamentals_cli_context.source.bundles[symbol] = _bundle(symbol, filing, caps)


@given(parsers.parse('stored fundamentals for "{symbol}" on "{day}"'))
def stored_fundamentals(fundamentals_cli_context, symbol, day, financial_repository):
    when = datetime.date.fromisoformat(day)
    financial_repository.add_income(
        IncomeStatement(
            symbol=symbol,
            date=when,
            netIncome=1.0,
            waso=10,
            consolidated_net_income=1.0,
        )
    )


@when(parsers.parse('I execute "{command}"'))
def execute_command(fundamentals_cli_context, command):
    args = split(command)
    fundamentals_cli_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=fundamentals_cli_context.deps
    )


@then("the command succeeds")
def command_succeeds(fundamentals_cli_context):
    assert_that(fundamentals_cli_context.result.exit_code, equal_to(0))


@then("the command fails")
def command_fails(fundamentals_cli_context):
    assert_that(fundamentals_cli_context.result.exit_code, not_(equal_to(0)))


@then(parsers.parse('the fundamentals source receives the symbols "{symbols}"'))
def source_receives_symbols(fundamentals_cli_context, symbols):
    received = [
        symbol for call in fundamentals_cli_context.source.calls for symbol in call[0]
    ]
    assert_that(received, equal_to(symbols.split(",")))


@then("the fundamentals source is not called")
def source_not_called(fundamentals_cli_context):
    assert_that(fundamentals_cli_context.source.calls, equal_to([]))


@then(parsers.parse("the import reports {count:d} new fundamental rows"))
def import_reports_rows(fundamentals_cli_context, count):
    assert_that(
        fundamentals_cli_context.result.output,
        contains_string(f"Imported {count} new fundamental row"),
    )


@then(parsers.parse('the output names "{symbol}"'))
def output_names(fundamentals_cli_context, symbol):
    assert_that(fundamentals_cli_context.result.output, contains_string(symbol))
