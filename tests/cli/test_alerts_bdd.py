"""BDD coverage for ranges and dry-run watch paths."""

from datetime import date, timedelta
from pathlib import Path
from shlex import split
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when
from typer.testing import CliRunner

import mrmkt.cli.main as cli
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.composition import cli_dependencies_for_testing
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "cli" / "alerts.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)
N_BARS = 60


@pytest.fixture
def alerts_context():
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


def _business_days(start: date, n: int) -> list:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _add_climb(local, symbol, dip: bool) -> None:
    closes = [100.0 * (1.002**i) for i in range(N_BARS)]
    if dip:
        for pos, factor in ((45, 0.90), (46, 0.93), (47, 0.97)):
            closes[pos] *= factor
    for day, close in zip(_business_days(START, N_BARS), closes, strict=True):
        low = close * (0.99 if dip else 0.995)
        local.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=close,
                high=close * 1.005,
                low=low,
                close=close,
                volume=1000.0,
            )
        )


@given("the alerts catalog contains these symbols:")
def alerts_catalog_contains_symbols(alerts_context, datatable):
    for row in _table_rows(datatable):
        alerts_context.local.add_ticker(
            Ticker(ticker=row["symbol"], exchange=row["exchange"], type=row["type"])
        )


@given(parsers.parse("each alerts symbol has a 60-bar steady climb tagged {tag}"))
def alerts_symbols_have_steady_climb(alerts_context, tag):
    for ticker in alerts_context.local.get_tickers():
        _add_climb(alerts_context.local, ticker.ticker, dip=False)
        alerts_context.local.add_tag(ticker.ticker, ticker.exchange, tag)


@given(parsers.parse("each alerts symbol has a 60-bar climb with a dip tagged {tag}"))
def alerts_symbols_have_climb_with_dip(alerts_context, tag):
    for ticker in alerts_context.local.get_tickers():
        _add_climb(alerts_context.local, ticker.ticker, dip=True)
        alerts_context.local.add_tag(ticker.ticker, ticker.exchange, tag)


@given(parsers.parse('{symbol} has a 60-bar climb with a dip'))
def symbol_has_dip(alerts_context, symbol):
    _add_climb(alerts_context.local, symbol, dip=True)


@given(parsers.parse('{symbol} has a 5-bar climb'))
def symbol_has_short_climb(alerts_context, symbol):
    price = 100.0
    for day in _business_days(START, 5):
        alerts_context.local.add_price(
            StockPrice(
                symbol=symbol, date=day, open=price, high=price * 1.005,
                low=price * 0.995, close=price, volume=1000.0,
            )
        )
        price *= 1.002


@when(parsers.parse('I execute "{command}"'))
def execute_alerts_command(alerts_context, command):
    args = split(command)
    alerts_context.result = CliRunner().invoke(
        cli.app, args[1:], obj=alerts_context.deps
    )


@then("the command succeeds")
def alerts_command_succeeds(alerts_context):
    assert alerts_context.result.exit_code == 0, alerts_context.result.output


@then("the command fails")
def alerts_command_fails(alerts_context):
    assert alerts_context.result.exit_code != 0, alerts_context.result.output


@then(parsers.parse('the output omits "{text}"'))
def alerts_output_omits(alerts_context, text):
    output = alerts_context.result.output
    stderr = getattr(alerts_context.result, "stderr", "") or ""
    assert text not in output and text not in stderr, output


@then(parsers.parse('the output mentions "{text}"'))
def alerts_output_mentions(alerts_context, text):
    output = alerts_context.result.output
    stderr = getattr(alerts_context.result, "stderr", "") or ""
    assert text in output or text in stderr, output
