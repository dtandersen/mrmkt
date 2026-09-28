from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    greater_than,
    has_length,
    not_,
)
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.common.clock import ClockStub
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "import_prices.feature"
scenarios(str(FEATURE))


class FakeAlpacaDataClient:
    def __init__(self):
        self.bars = {}
        self.requests = []
        self.error = None

    def get_stock_bars(self, request):
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        symbols = request.symbol_or_symbols
        if isinstance(symbols, str):
            symbols = [symbols]
        return SimpleNamespace(
            data={symbol: self.bars.get(symbol, []) for symbol in symbols}
        )


@pytest.fixture
def price_import_context(financial_repository, requests_mock):
    clock = ClockStub()
    clock.set_time(date(2026, 6, 28))
    context = SimpleNamespace(
        alpaca=FakeAlpacaDataClient(),
        yahoo_http=requests_mock,
        clock=clock,
        result=None,
    )
    context.deps = cli_dependencies_for_testing(
        repository=financial_repository,
        clock=context.clock,
        alpaca_data_client=context.alpaca,
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


def _stock_price(row):
    return StockPrice(
        symbol=row["symbol"],
        date=date.fromisoformat(row["date"]),
        open=float(row["open"]),
        high=float(row["high"]),
        low=float(row["low"]),
        close=float(row["close"]),
        volume=float(row["volume"]),
    )


def _set_alpaca_bars(context, datatable):
    for row in _table_rows(datatable):
        bar = SimpleNamespace(
            timestamp=datetime.combine(
                date.fromisoformat(row["date"]),
                time.min,
                tzinfo=UTC,
            ),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )
        context.alpaca.bars.setdefault(row["symbol"], []).append(bar)


@given("Alpaca returns these daily bars:")
def alpaca_returns_daily_bars(price_import_context, datatable):
    _set_alpaca_bars(price_import_context, datatable)


@given("the local ticker catalog contains these symbols:")
def local_catalog_contains_symbols(
    price_import_context, datatable, financial_repository
):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse('ticker "{symbol}" on "{exchange}" already has tag "{tag}"'))
def ticker_already_has_tag(
    price_import_context, symbol, exchange, tag, financial_repository
):
    financial_repository.add_tag(symbol, exchange, tag)


@given("the local price catalog already contains these daily bars:")
def seed_local_price_catalog(price_import_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_price(_stock_price(row))


@given(parsers.parse('the fake clock says today is "{today}"'))
def fake_clock_says_today(price_import_context, today):
    price_import_context.clock.set_time(date.fromisoformat(today))


@given("the Alpaca price request fails")
def alpaca_price_request_fails(price_import_context):
    price_import_context.alpaca.error = RuntimeError("market data unavailable")


@given(parsers.parse('Yahoo Finance returns VIX close "{close}" for "{day}"'))
def yahoo_finance_returns_vix_close(price_import_context, close, day):
    bar_date = date.fromisoformat(day)
    timestamp = int(datetime.combine(bar_date, time.min, tzinfo=UTC).timestamp())
    price_import_context.yahoo_http.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
        json={
            "chart": {
                "result": [
                    {
                        "timestamp": [timestamp],
                        "indicators": {
                            "quote": [
                                {
                                    "open": [15.61],
                                    "high": [15.94],
                                    "low": [14.68],
                                    "close": [float(close)],
                                    "volume": [0],
                                }
                            ],
                            "adjclose": [{"adjclose": [float(close)]}],
                        },
                    }
                ],
                "error": None,
            }
        },
    )


@when(parsers.parse('I execute "{command}"'))
def execute_price_command(price_import_context, command):
    args = split(command)
    price_import_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=price_import_context.deps
    )


@then("the command succeeds")
def price_command_succeeds(price_import_context):
    assert_that(price_import_context.result.exit_code, equal_to(0))


@then("the command fails")
def price_command_fails(price_import_context):
    assert_that(price_import_context.result.exit_code, not_(equal_to(0)))


@then(parsers.parse('Alpaca receives the symbols "{symbols}"'))
def alpaca_receives_symbols(price_import_context, symbols):
    expected = symbols.split(",")
    requested = [
        symbol
        for request in price_import_context.alpaca.requests
        for symbol in request.symbol_or_symbols
    ]
    assert_that(requested, equal_to(expected))


@then(parsers.parse('Alpaca receives the date range from "{start}" to "{end}"'))
def alpaca_receives_date_range(price_import_context, start, end):
    assert_that(
        price_import_context.alpaca.requests,
        has_length(greater_than(0)),
    )
    for request in price_import_context.alpaca.requests:
        assert_that(request.start.date(), equal_to(date.fromisoformat(start)))
        assert_that(request.end.date(), equal_to(date.fromisoformat(end)))


@then("the local price catalog contains these daily bars:")
def assert_local_price_catalog_contains_bars(
    price_import_context, datatable, financial_repository
):
    expected = {
        (
            price.symbol,
            price.date,
            price.open,
            price.high,
            price.low,
            price.close,
            price.volume,
        )
        for price in map(_stock_price, _table_rows(datatable))
    }
    actual = {
        (
            price.symbol,
            price.date,
            price.open,
            price.high,
            price.low,
            price.close,
            price.volume,
        )
        for price in financial_repository.prices.all()
    }
    assert_that(actual, equal_to(expected))


@then(
    parsers.parse(
        'the local price catalog contains exactly one "{symbol}" bar on "{day}"'
    )
)
def local_price_is_unique(price_import_context, symbol, day, financial_repository):
    matching = [
        price
        for price in financial_repository.list_prices(symbol)
        if price.date == date.fromisoformat(day)
    ]
    assert_that(matching, has_length(1))


@then(parsers.re(r"the import reports (?P<count>\d+) new daily bars?"))
def import_reports_bar_count(price_import_context, count):
    assert_that(
        price_import_context.result.output,
        contains_string(f"Imported {count} new daily bar"),
    )


@then("no Alpaca request is sent")
def no_alpaca_request_is_sent(price_import_context):
    assert_that(price_import_context.alpaca.requests, equal_to([]))


@then(
    parsers.parse('Yahoo Finance receives VIX history from "{start}" through "{end}"')
)
def yahoo_finance_receives_vix_history(price_import_context, start, end):
    assert_that(price_import_context.yahoo_http.call_count, equal_to(1))
    request = price_import_context.yahoo_http.last_request
    assert_that(request.method, equal_to("GET"))
    assert_that(request.path.lower(), equal_to("/v8/finance/chart/%5evix"))
    expected_start = int(
        datetime.combine(date.fromisoformat(start), time.min, tzinfo=UTC).timestamp()
    )
    expected_end = int(
        datetime.combine(
            date.fromisoformat(end) + timedelta(days=1),
            time.min,
            tzinfo=UTC,
        ).timestamp()
    )
    assert_that(request.qs["period1"], equal_to([str(expected_start)]))
    assert_that(request.qs["period2"], equal_to([str(expected_end)]))


@then("the local price catalog remains empty")
def local_price_catalog_remains_empty(price_import_context, financial_repository):
    assert_that(financial_repository.prices.all(), equal_to([]))
