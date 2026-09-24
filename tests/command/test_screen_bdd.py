"""BDD coverage for ScreenUseCase, driven directly (no CLI)."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.command.screen import ScreenRequest, ScreenUseCase, render_csv

FEATURE = Path(__file__).parent.parent / "features" / "command" / "screen.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


@pytest.fixture
def screen_context():
    return SimpleNamespace(local=None, result=None, as_of=None, csvs=[])


def _business_days(start: date, n: int) -> list:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


@given("a clean price catalog")
def clean_catalog(screen_context):
    screen_context.local = InMemoryFinancialRepository()


@given(parsers.parse('symbol "{symbol}" is also tagged "{tag}"'))
def symbol_also_tagged(screen_context, symbol, tag):
    screen_context.local.add_tag(symbol, "NASDAQ", tag)


@given(parsers.parse('symbol "{symbol}" has a 50-bar climb at drift {drift:f} tagged "{tag}"'))
def symbol_has_short_climb(screen_context, symbol, drift, tag):
    repo = screen_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    price = 100.0
    for day in _business_days(START, 50):
        price *= 1 + drift
        repo.add_price(
            StockPrice(
                symbol=symbol, date=day, open=price, high=price * 1.005,
                low=price * 0.995, close=price, volume=100000.0,
            )
        )
    repo.add_tag(symbol, "NASDAQ", tag)


@given(parsers.parse('symbol "{symbol}" has a 250-bar climb at drift {drift:f} tagged "{tag}"'))
def symbol_has_climb(screen_context, symbol, drift, tag):
    repo = screen_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    price = 100.0
    for day in _business_days(START, 250):
        price *= 1 + drift
        repo.add_price(
            StockPrice(
                symbol=symbol, date=day, open=price, high=price * 1.005,
                low=price * 0.995, close=price, volume=100000.0,
            )
        )
    repo.add_tag(symbol, "NASDAQ", tag)


@when(parsers.parse('I screen tag "{tag}"'))
def screen_tag(screen_context, tag):
    screen_context.result = ScreenUseCase(screen_context.local).execute(
        ScreenRequest(include_tags=[tag])
    )


@when("I screen tag \"universe\" as of 30 bars before the last bar")
def screen_as_of(screen_context):
    as_of = _business_days(START, 250)[-31]
    screen_context.as_of = as_of
    screen_context.result = ScreenUseCase(screen_context.local).execute(
        ScreenRequest(include_tags=["universe"], as_of=as_of)
    )


@when(parsers.parse('I screen tag "{tag}" excluding "{excluded}"'))
def screen_excluding(screen_context, tag, excluded):
    screen_context.result = ScreenUseCase(screen_context.local).execute(
        ScreenRequest(include_tags=[tag], exclude_tags=[excluded])
    )


@when(parsers.parse('I screen tag "{tag}" with top {top:d}'))
def screen_top(screen_context, tag, top):
    use_case = ScreenUseCase(screen_context.local)
    screen_context.full = use_case.execute(ScreenRequest(include_tags=[tag]))
    screen_context.result = use_case.execute(ScreenRequest(include_tags=[tag], top_n=top))


@when(parsers.parse('I screen tag "{tag}" with max stale days {days:d}'))
def screen_max_stale(screen_context, tag, days):
    screen_context.result = ScreenUseCase(screen_context.local).execute(
        ScreenRequest(include_tags=[tag], max_stale_days=days)
    )


@when(parsers.parse('I screen tag "{tag}" with min-price {floor:f}'))
def screen_min_price(screen_context, tag, floor):
    screen_context.result = ScreenUseCase(screen_context.local).execute(
        ScreenRequest(include_tags=[tag], min_price=floor)
    )


@when(parsers.parse('I screen tag "{tag}" twice'))
def screen_twice(screen_context, tag):
    use_case = ScreenUseCase(screen_context.local)
    request = ScreenRequest(include_tags=[tag])
    screen_context.result = use_case.execute(request)
    screen_context.csvs = [render_csv(use_case.execute(request)) for _ in range(2)]


@when(parsers.parse('I screen in mode "{mode}"'))
def screen_mode(screen_context, mode):
    try:
        screen_context.result = ScreenUseCase(screen_context.local).execute(
            ScreenRequest(mode=mode)
        )
        screen_context.error = None
    except ValueError as error:
        screen_context.result = None
        screen_context.error = str(error)


@then(parsers.parse("the screen succeeds with {count:d} ranked rows"))
def screen_row_count(screen_context, count):
    assert screen_context.result is not None
    assert len(screen_context.result.rows) == count


@then(parsers.parse('"{better}" ranks above "{worse}"'))
def rank_order(screen_context, better, worse):
    order = [row.symbol for row in screen_context.result.rows]
    assert order.index(better) < order.index(worse)


@then("every row has last_date on or before as-of")
def rows_within_as_of(screen_context):
    for row in screen_context.result.rows:
        assert row.last_date <= screen_context.as_of


@then("data vintage equals as-of")
def vintage_equals_as_of(screen_context):
    assert screen_context.result.data_vintage == screen_context.as_of


@then(parsers.parse('exclusions report "{reason}"'))
def exclusions_report(screen_context, reason):
    assert reason in screen_context.result.excluded


@then("both CSV renders are identical")
def csv_deterministic(screen_context):
    assert screen_context.csvs[0] == screen_context.csvs[1]


@then(parsers.parse('the screen fails naming "{text}"'))
def screen_fails(screen_context, text):
    assert screen_context.result is None
    assert text in screen_context.error


@then(parsers.parse('the rows are exactly "{first}" and "{second}"'))
def rows_exactly(screen_context, first, second):
    assert sorted(r.symbol for r in screen_context.result.rows) == [first, second]


@then("data vintage equals the full-universe vintage")
def vintage_full_universe(screen_context):
    assert len(screen_context.full.rows) > 1
    assert len(screen_context.result.rows) == 1
    assert screen_context.result.data_vintage == screen_context.full.data_vintage


@then(parsers.parse('the CSV header echoes "{text}"'))
def csv_echoes(screen_context, text):
    assert text in render_csv(screen_context.result)


@then("scores descend with symbol tiebreak")
def scores_ordered(screen_context):
    rows = screen_context.result.rows
    scores = [r.score for r in rows]
    assert scores == sorted(scores, reverse=True)
    assert rows[0].rank == 1


@then("the CSV header reports current membership vintage")
def membership_vintage(screen_context):
    assert "universe_membership_vintage=current" in render_csv(screen_context.result)
