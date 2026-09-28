"""BDD coverage for ImportFundamentals and ShowFundamentals, driven directly."""

import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.command.import_fundamentals import (
    ImportFundamentals,
    ImportFundamentalsRequest,
)
from mrmkt.command.show_fundamentals import ShowFundamentals, ShowFundamentalsRequest
from mrmkt.common.clock import ClockStub
from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.income_statement import IncomeStatement
from mrmkt.entity.stock_price import StockPrice
from mrmkt.ext.backend import InMemoryBackend
from mrmkt.ext.tiingo_fundamentals import DailyMarketCap, SymbolFundamentals

scenarios(
    str(
        Path(__file__).parent.parent
        / "features"
        / "command"
        / "import_fundamentals.feature"
    ),
    str(
        Path(__file__).parent.parent
        / "features"
        / "command"
        / "show_fundamentals.feature"
    ),
)

TODAY = datetime.date(2024, 4, 30)


class FakeFundamentalsSource:
    def __init__(self, bundles_by_symbol=None, failing=(), flaky=None):
        self.bundles_by_symbol = dict(bundles_by_symbol or {})
        self.failing = set(failing)
        self.flaky = dict(flaky or {})
        self.calls = []

    def get_fundamentals(self, symbols, end):
        key = ",".join(symbols)
        self.calls.append((list(symbols), end))
        if key in self.failing:
            raise ConnectionError("boom")
        if self.flaky.get(key, 0) > 0:
            self.flaky[key] -= 1
            raise ConnectionError("transient outage")
        return {
            symbol: self.bundles_by_symbol[symbol]
            for symbol in symbols
            if symbol in self.bundles_by_symbol
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
                non_current_assets=3000000000.0,
                inventories=100000000.0,
                receivables=200000000.0,
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
                deprec=10000000.0,
            )
        ],
        shares_by_date={filing_date: 1000.0},
        daily_caps=[
            DailyMarketCap(
                date=datetime.date.fromisoformat(day),
                market_cap=float(cap),
            )
            for day, cap in (pair.split(":") for pair in caps.split(",") if pair)
        ],
    )


@pytest.fixture
def fundamentals_context():
    return SimpleNamespace(
        store=None,
        source=None,
        result=None,
        error=None,
        delays=None,
        progress=None,
        batch_size=None,
    )


def _source(fundamentals_context):
    if fundamentals_context.source is None:
        fundamentals_context.source = FakeFundamentalsSource()
    return fundamentals_context.source


def _run_import(fundamentals_context, request):
    clock = ClockStub()
    clock.set_time(TODAY)
    fundamentals_context.delays = []
    fundamentals_context.progress = []
    command = ImportFundamentals(
        _source(fundamentals_context),
        fundamentals_context.store,
        fundamentals_context.store,
        fundamentals_context.store,
        clock,
        sleep=fundamentals_context.delays.append,
        on_progress=lambda done, total: fundamentals_context.progress.append(
            (done, total)
        ),
    )
    if fundamentals_context.batch_size is not None:
        command.batch_size = fundamentals_context.batch_size
    outcome = command.execute(request)
    if outcome.is_success():
        assert outcome.result is not None
        fundamentals_context.result = outcome.result.result
        fundamentals_context.error = None
    else:
        fundamentals_context.result = None
        fundamentals_context.error = "; ".join(outcome.errors)


@given("a clean fundamentals store")
def clean_store(fundamentals_context):
    fundamentals_context.store = InMemoryBackend()


@given("stored bars:")
def stored_bars(fundamentals_context, datatable):
    for row in datatable[1:]:
        fundamentals_context.store.add_price(
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


@given(
    parsers.parse(
        'a fake fundamentals source serving "{symbol}" with filing "{filing}" and caps "{caps}"'
    )
)
def source_serving(fundamentals_context, symbol, filing, caps):
    _source(fundamentals_context).bundles_by_symbol[symbol] = _bundle(
        symbol, filing, caps
    )


@given(parsers.parse('a fake fundamentals source failing batch "{batch}"'))
def source_failing(fundamentals_context, batch):
    _source(fundamentals_context).failing.add(batch)


@given(parsers.parse('batch "{batch}" fails {count:d} times before succeeding'))
def source_flaky(fundamentals_context, batch, count):
    _source(fundamentals_context).flaky[batch] = count


@given(parsers.parse("the import batch size is {size:d}"))
def import_batch_size(fundamentals_context, size):
    fundamentals_context.batch_size = size


@given(parsers.parse('stored fundamentals for "{symbol}" on "{first}" and "{second}"'))
def stored_fundamentals(fundamentals_context, symbol, first, second):
    for day in (first, second):
        when = datetime.date.fromisoformat(day)
        fundamentals_context.store.add_income(
            IncomeStatement(
                symbol=symbol,
                date=when,
                netIncome=1.0,
                waso=10,
                consolidated_net_income=1.0,
            )
        )


@when(parsers.parse('I import "{symbols}" fundamentals'))
def run_import(fundamentals_context, symbols):
    _run_import(
        fundamentals_context,
        ImportFundamentalsRequest(provider="tiingo", symbols=symbols.split(",")),
    )


@when(parsers.parse('I import "{symbols}" fundamentals again'))
def run_import_again(fundamentals_context, symbols):
    _run_import(
        fundamentals_context,
        ImportFundamentalsRequest(provider="tiingo", symbols=symbols.split(",")),
    )


@when(parsers.parse('I show fundamentals for "{symbol}"'))
def run_show(fundamentals_context, symbol):
    command = ShowFundamentals(fundamentals_context.store)
    outcome = command.execute(ShowFundamentalsRequest(symbol=symbol))
    fundamentals_context.result = outcome if outcome.is_success() else None
    fundamentals_context.error = (
        None if outcome.is_success() else "; ".join(outcome.errors)
    )
    if outcome.is_success():
        fundamentals_context.view = outcome.result


@then(parsers.parse('{count:d} income statements are stored for "{symbol}"'))
def incomes_stored(fundamentals_context, count, symbol):
    assert_that(
        len(fundamentals_context.store.list_income_statements(symbol)),
        equal_to(count),
    )


@then(parsers.parse('{count:d} balance sheets are stored for "{symbol}"'))
def balances_stored(fundamentals_context, count, symbol):
    assert_that(
        len(fundamentals_context.store.list_balance_sheets(symbol)), equal_to(count)
    )


@then(parsers.parse('{count:d} cash flows are stored for "{symbol}"'))
def cashflows_stored(fundamentals_context, count, symbol):
    assert_that(
        len(fundamentals_context.store.list_cash_flows(symbol)), equal_to(count)
    )


@then(parsers.parse('{count:d} enterprise values are stored for "{symbol}"'))
def enterprise_stored(fundamentals_context, count, symbol):
    assert_that(
        len(fundamentals_context.store.list_enterprise_value(symbol)),
        equal_to(count),
    )


@then(parsers.parse("{count:d} fundamentals rows were imported"))
def rows_imported(fundamentals_context, count):
    assert_that(fundamentals_context.result.imported, equal_to(count))


@then(
    parsers.parse(
        'the enterprise value for "{symbol}" on "{day}" uses price {price:g} '
        "with {shares:g} shares and cap {cap:g}"
    )
)
def enterprise_row(fundamentals_context, symbol, day, price, shares, cap):
    rows = [
        row
        for row in fundamentals_context.store.list_enterprise_value(symbol)
        if row.date == datetime.date.fromisoformat(day)
    ]
    assert_that(len(rows), equal_to(1))
    assert_that(rows[0].stock_price, equal_to(float(price)))
    assert_that(rows[0].shares_outstanding, equal_to(float(shares)))
    assert_that(rows[0].market_cap, equal_to(float(cap)))


@then(parsers.parse('the batch "{batch}" is recorded failed'))
def batch_failed(fundamentals_context, batch):
    assert_that(
        [batch.split(",")], equal_to(fundamentals_context.result.failed_batches)
    )


@then(parsers.parse("the fundamentals source was called {count:d} times"))
def source_called(fundamentals_context, count):
    assert_that(len(fundamentals_context.source.calls), equal_to(count))


@then("the retry delays were:")
def retry_delays_were(fundamentals_context, datatable):
    assert_that(
        [float(row[0]) for row in datatable[1:]],
        equal_to(fundamentals_context.delays),
    )


@then("progress reports were:")
def progress_reports_were(fundamentals_context, datatable):
    assert_that(
        [(int(row[0]), int(row[1])) for row in datatable[1:]],
        equal_to(fundamentals_context.progress),
    )


@then("the show succeeds")
def show_succeeds(fundamentals_context):
    assert_that(fundamentals_context.error, equal_to(None))


@then(parsers.parse('the income dates are "{days}"'))
def income_dates(fundamentals_context, days):
    assert_that(
        [row.date.isoformat() for row in fundamentals_context.view.incomes],
        equal_to(days.split(",")),
    )


@then(parsers.parse('the show fails naming "{message}"'))
def show_fails(fundamentals_context, message):
    assert_that(fundamentals_context.result, equal_to(None))
    assert_that(fundamentals_context.error, contains_string(message))
