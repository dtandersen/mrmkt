"""BDD coverage for the read-only web view (Playwright + page objects)."""

import http.client
import logging
import socket
import threading
import time
from datetime import date
from types import SimpleNamespace

import pytest
import uvicorn
from hamcrest import assert_that, contains_string, equal_to
from playwright.sync_api import sync_playwright
from pytest_bdd import given, parsers, scenarios, then, when
from tests.web_pages import (
    ChartDataPage,
    IndexPage,
    PricesPage,
    SymbolLookupPage,
    SymbolsPage,
    TriggersPage,
)

from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.entity.trigger import Trigger
from mrmkt.web.app import create_web_app

scenarios(
    "features/web/symbols.feature",
    "features/web/prices.feature",
    "features/web/prices_chart.feature",
    "features/web/triggers.feature",
)


def _free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_server(host, port, timeout=10.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            connection = http.client.HTTPConnection(host, port, timeout=1)
            try:
                connection.request("GET", "/")
                status = connection.getresponse().status
            finally:
                connection.close()
            if status < 500:
                return
        except Exception as error:
            logging.debug("waiting for web server: %s", error)
        if time.monotonic() > deadline:
            raise TimeoutError(f"web server did not start on {host}:{port}")
        time.sleep(0.05)


@pytest.fixture(scope="session")
def web_browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def web_context(web_browser, financial_repository):
    deps = cli_dependencies_for_testing(repository=financial_repository)
    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(
            create_web_app(lambda: deps),
            host="127.0.0.1",
            port=port,
            log_level="error",
            access_log=False,
        )
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    _wait_for_server("127.0.0.1", port)
    page = web_browser.new_page()
    context = SimpleNamespace(
        page=page,
        base_url=base_url,
        symbols=SymbolsPage(page, base_url),
        prices=PricesPage(page, base_url),
        chart=ChartDataPage(page, base_url),
        lookup=SymbolLookupPage(page, base_url),
        triggers=TriggersPage(page, base_url),
        index=IndexPage(page, base_url),
    )
    yield context
    page.close()
    server.should_exit = True
    thread.join(timeout=10)


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the local ticker catalog contains these symbols:")
def local_catalog_contains_symbols(web_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given("the local ticker catalog is empty")
def local_catalog_is_empty(web_context, financial_repository):
    assert_that(financial_repository.get_tickers(), equal_to([]))


@given(parsers.parse('ticker "{symbol}" on "{exchange}" already has tag "{tag}"'))
def ticker_already_has_tag(web_context, symbol, exchange, tag, financial_repository):
    financial_repository.add_tag(symbol, exchange, tag)


@given("the local price catalog contains these daily bars:")
def local_price_catalog_contains_bars(web_context, datatable, financial_repository):
    for row in _table_rows(datatable):
        financial_repository.add_price(
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


@given(parsers.parse('trigger "{name}" exists'))
def trigger_exists(web_context, name, financial_repository):
    financial_repository.add_trigger(
        Trigger(
            id=None,
            name=name,
            symbol="AAA",
            signal="risk-range",
            operator="crossing-down",
            value=None,
            frequency="once_per_rearm",
            expires_at=None,
            message="",
            enabled=True,
        )
    )


@when(parsers.parse('I open "{path}"'))
def open_path(web_context, path):
    if path == "/":
        web_context.index.open()
        web_context.status = web_context.index.status()
    elif path.startswith("/fragments/symbols/lookup"):
        web_context.lookup.open(path[len("/fragments/symbols/lookup") :])
        web_context.status = web_context.lookup.status()
    elif path.startswith("/fragments/symbols"):
        web_context.symbols.open(path[len("/fragments/symbols") :])
        web_context.status = web_context.symbols.status()
    elif path.startswith("/fragments/prices/chart"):
        web_context.chart.open(path[len("/fragments/prices/chart") :])
        web_context.status = web_context.chart.status()
    elif path.startswith("/fragments/prices"):
        web_context.prices.open(path[len("/fragments/prices") :])
        web_context.status = web_context.prices.status()
    elif path.startswith("/fragments/triggers"):
        web_context.triggers.open(path[len("/fragments/triggers") :])
        web_context.status = web_context.triggers.status()
    else:
        raise AssertionError(f"no page object for {path}")


@then("the web command succeeds")
def web_command_succeeds(web_context):
    assert_that(web_context.status, equal_to(200))


@then(parsers.parse("the web command fails with status {status:d}"))
def web_command_fails(web_context, status):
    assert_that(web_context.status, equal_to(status))


@then("the symbol fragment lists these rows in order:")
def symbol_fragment_lists_rows(web_context, datatable):
    assert_that(
        [
            f"{symbol} | {exchange} | {kind}"
            for symbol, exchange, kind in web_context.symbols.rows()
        ],
        equal_to(
            [
                f"{row['symbol']} | {row['exchange']} | {row['type']}"
                for row in _table_rows(datatable)
            ]
        ),
    )


@then("the fragment says no symbols were found")
def fragment_says_no_symbols(web_context):
    assert_that(web_context.symbols.empty_text(), contains_string("No symbols found."))


@then("the fragment reports an error")
def fragment_reports_error(web_context):
    assert_that(web_context.symbols.empty_text(), contains_string("tags must"))


@then("the price fragment lists these rows in order:")
def price_fragment_lists_rows(web_context, datatable):
    assert_that(
        [
            f"{symbol} | {day} | {float(close):g}"
            for symbol, day, close in web_context.prices.rows()
        ],
        equal_to(
            [
                f"{row['symbol']} | {row['date']} | {float(row['close']):g}"
                for row in _table_rows(datatable)
            ]
        ),
    )


@then("the fragment says no prices were found")
def fragment_says_no_prices(web_context):
    assert_that(web_context.prices.empty_text(), contains_string("No prices found."))


@then("the chart data lists these bars in order:")
def chart_data_lists_bars(web_context, datatable):
    assert_that(
        [
            f"{bar['time']} | {float(bar['open']):g} | "
            f"{float(bar['high']):g} | {float(bar['low']):g} | "
            f"{float(bar['close']):g}"
            for bar in web_context.chart.bars()
        ],
        equal_to(
            [
                f"{row['time']} | {float(row['open']):g} | "
                f"{float(row['high']):g} | {float(row['low']):g} | "
                f"{float(row['close']):g}"
                for row in _table_rows(datatable)
            ]
        ),
    )


@then("the chart data is empty")
def chart_data_is_empty(web_context):
    assert_that(web_context.chart.bars(), equal_to([]))


@then("the symbol lookup lists these tickers in order:")
def symbol_lookup_lists_tickers(web_context, datatable):
    assert_that(
        [
            f"{row['ticker']} | {row['exchange']} | {row['type']}"
            for row in web_context.lookup.tickers()
        ],
        equal_to(
            [
                f"{row['ticker']} | {row['exchange']} | {row['type']}"
                for row in _table_rows(datatable)
            ]
        ),
    )


@then("the symbol lookup is empty")
def symbol_lookup_is_empty(web_context):
    assert_that(web_context.lookup.tickers(), equal_to([]))


@then("the index opens on the S&P 500 chart")
def index_opens_on_chart(web_context):
    assert_that(web_context.index.has_chart(), equal_to(True))
    assert_that(web_context.index.chart_symbol_default(), equal_to("SPY"))


@then(parsers.parse('the trigger fragment lists "{name}"'))
def trigger_fragment_lists(web_context, name):
    assert_that(web_context.triggers.names(), equal_to([name]))


@then("the fragment says no triggers were found")
def fragment_says_no_triggers(web_context):
    assert_that(
        web_context.triggers.empty_text(), contains_string("No triggers found.")
    )


@then(parsers.parse("the index references the {name} fragment"))
def index_references_fragment(web_context, name):
    assert_that(
        web_context.index.section_fragment(name), equal_to(f"/fragments/{name}")
    )
