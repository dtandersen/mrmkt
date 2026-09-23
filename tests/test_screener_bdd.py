"""BDD coverage for screen / signals current / prices freshness paths."""

from datetime import date, timedelta
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli as cli
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent / "features" / "screener.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


@pytest.fixture
def screener_context(monkeypatch):
    context = SimpleNamespace(
        local=InMemoryFinancialRepository(),
        result=None,
    )
    monkeypatch.setattr(
        cli,
        "create_local_ticker_repository",
        lambda: (context.local, lambda: None),
    )
    return context


def _table_rows(datatable):
    headers = [str(header) for header in datatable[0]]
    return [dict(zip(headers, row, strict=True)) for row in datatable[1:]]


@given("the screener catalog contains these symbols:")
def screener_catalog_contains_symbols(screener_context, datatable):
    for row in _table_rows(datatable):
        screener_context.local.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse("each screener symbol has a 250-bar climb tagged {tag}"))
def screener_symbols_have_climb(screener_context, tag):
    day = START
    closes = []
    price = 100.0
    while len(closes) < 250:
        if day.weekday() < 5:
            closes.append((day, price))
            price *= 1.002
        day += timedelta(days=1)
    for ticker in screener_context.local.get_tickers():
        for bar_day, close in closes:
            screener_context.local.add_price(
                StockPrice(
                    symbol=ticker.ticker,
                    date=bar_day,
                    open=close,
                    high=close * 1.005,
                    low=close * 0.995,
                    close=close,
                    volume=100000.0,
                )
            )
        screener_context.local.add_tag(ticker.ticker, ticker.exchange, tag)


@when(parsers.parse('I execute "{command}"'))
def execute_screener_command(screener_context, command):
    args = split(command)
    screener_context.result = CliRunner().invoke(cli.app, args[1:])


@then("the command succeeds")
def screener_command_succeeds(screener_context):
    assert screener_context.result.exit_code == 0, screener_context.result.output


@then(parsers.parse('the output mentions "{text}"'))
def screener_output_mentions(screener_context, text):
    output = screener_context.result.output
    stderr = getattr(screener_context.result, "stderr", "") or ""
    assert text in output or text in stderr, output
