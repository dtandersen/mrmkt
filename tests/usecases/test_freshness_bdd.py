"""BDD coverage for FreshnessUseCase, driven directly (no CLI)."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.freshness import FreshnessRequest, FreshnessUseCase, render_csv

FEATURE = Path(__file__).parent.parent / "features" / "command" / "freshness.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


@pytest.fixture
def freshness_context():
    return SimpleNamespace(local=None, result=None, today=None)


def _business_days(start: date, n: int) -> list:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _add_bar(repo, symbol, day, close, high=None, low=None, volume=1000.0):
    repo.add_price(
        StockPrice(
            symbol=symbol, date=day, open=close,
            high=high if high is not None else close * 1.005,
            low=low if low is not None else close * 0.995,
            close=close, volume=volume,
        )
    )


@given("a clean price catalog")
def clean_catalog(freshness_context):
    freshness_context.local = InMemoryFinancialRepository()


@given(parsers.parse('symbol "{symbol}" has 30 daily bars ending 10 days before today'))
def symbol_has_old_bars(freshness_context, symbol):
    repo = freshness_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    days = _business_days(START, 30)
    freshness_context.today = days[-1] + timedelta(days=10)
    price = 100.0
    for day in days:
        _add_bar(repo, symbol, day, price)
        price *= 1.001


@given(parsers.parse('symbol "{symbol}" has a bar with high below low and a bar with zero volume'))
def symbol_has_bad_bars(freshness_context, symbol):
    repo = freshness_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    days = _business_days(START, 10)
    for pos, day in enumerate(days):
        _add_bar(
            repo, symbol, day, 50.0,
            high=49.0 if pos == 0 else None,
            volume=0.0 if pos == 5 else 1000.0,
        )
    freshness_context.today = days[-1]


@given(parsers.parse('symbol "{symbol}" halves overnight once'))
def symbol_has_gap(freshness_context, symbol):
    repo = freshness_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    days = _business_days(START, 20)
    for day in days[:10]:
        _add_bar(repo, symbol, day, 100.0)
    for day in days[10:]:
        _add_bar(repo, symbol, day, 50.0)
    freshness_context.today = days[-1]


@given(parsers.parse('symbol "{symbol}" has a catalog entry but no bars'))
def symbol_has_no_bars(freshness_context, symbol):
    repo = freshness_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    freshness_context.today = date(2024, 1, 10)


@when("I check freshness today")
def check_freshness(freshness_context):
    freshness_context.result = FreshnessUseCase(freshness_context.local).execute(
        FreshnessRequest(today=freshness_context.today)
    )


def _row(freshness_context, symbol):
    return next(r for r in freshness_context.result.rows if r.symbol == symbol)


@then(parsers.parse('"{symbol}" is flagged "{flag}" with staleness {days:d} days'))
def stale_flagged(freshness_context, symbol, flag, days):
    row = _row(freshness_context, symbol)
    assert flag in row.flags
    assert row.staleness_days == days


@then(parsers.parse('"{symbol}" is flagged "{flag}"'))
def flagged(freshness_context, symbol, flag):
    assert flag in _row(freshness_context, symbol).flags


@then("the CSV calls the flags suspicion heuristics with no adjustment provenance")
def heuristic_caveats(freshness_context):
    text = render_csv(freshness_context.result)
    assert "suspicion heuristics" in text
    assert "no adjustment" in text
