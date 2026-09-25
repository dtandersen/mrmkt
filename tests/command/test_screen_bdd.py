"""BDD coverage for ScreenSymbols, driven directly (no CLI)."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import (
    assert_that,
    contains_string,
    equal_to,
    has_key,
    less_than_or_equal_to,
)
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.command.screen import ScreenSymbols, ScreenSymbolsRequest, render_csv
from mrmkt.common.clock import ClockStub
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "command" / "screen.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


@pytest.fixture
def screen_context():
    clock = ClockStub()
    clock.set_time(date(2024, 6, 30))
    return SimpleNamespace(local=None, result=None, as_of=None, csvs=[], clock=clock)


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


@given(
    parsers.parse(
        'symbol "{symbol}" has a 50-bar climb at drift {drift:f} tagged "{tag}"'
    )
)
def symbol_has_short_climb(screen_context, symbol, drift, tag):
    repo = screen_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    price = 100.0
    for day in _business_days(START, 50):
        price *= 1 + drift
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=100000.0,
            )
        )
    repo.add_tag(symbol, "NASDAQ", tag)


@given(
    parsers.parse(
        'symbol "{symbol}" has a 250-bar climb at drift {drift:f} tagged "{tag}"'
    )
)
def symbol_has_climb(screen_context, symbol, drift, tag):
    repo = screen_context.local
    repo.add_ticker(Ticker(ticker=symbol, exchange="NASDAQ", type="us_equity"))
    price = 100.0
    for day in _business_days(START, 250):
        price *= 1 + drift
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=price,
                high=price * 1.005,
                low=price * 0.995,
                close=price,
                volume=100000.0,
            )
        )
    repo.add_tag(symbol, "NASDAQ", tag)


def _screen(screen_context, **kwargs):
    command = ScreenSymbols(screen_context.local, screen_context.clock)
    return command.execute(ScreenSymbolsRequest(**kwargs))


@when(parsers.parse('I screen tag "{tag}"'))
def screen_tag(screen_context, tag):
    screen_context.result = _screen(screen_context, tags=[tag])


@when('I screen tag "universe" as of 30 bars before the last bar')
def screen_as_of(screen_context):
    as_of = _business_days(START, 250)[-31]
    screen_context.as_of = as_of
    screen_context.result = _screen(
        screen_context, tags=["universe"], as_of=as_of.isoformat()
    )


@when(parsers.parse('I screen tag "{tag}" excluding "{excluded}"'))
def screen_excluding(screen_context, tag, excluded):
    screen_context.result = _screen(screen_context, tags=[tag], exclude_tags=[excluded])


@when(parsers.parse('I screen tag "{tag}" with top {top:d}'))
def screen_top(screen_context, tag, top):
    full = _screen(screen_context, tags=[tag])
    assert full.is_success()
    assert full.result is not None
    screen_context.full = full.result
    screen_context.result = _screen(screen_context, tags=[tag], top=top)


@when(parsers.parse('I screen tag "{tag}" with max stale days {days:d}'))
def screen_max_stale(screen_context, tag, days):
    screen_context.result = _screen(screen_context, tags=[tag], max_stale_days=days)


@when(parsers.parse('I screen tag "{tag}" with min-price {floor:f}'))
def screen_min_price(screen_context, tag, floor):
    screen_context.result = _screen(screen_context, tags=[tag], min_price=floor)


@when(parsers.parse('I screen tag "{tag}" twice'))
def screen_twice(screen_context, tag):
    first = _screen(screen_context, tags=[tag])
    second = _screen(screen_context, tags=[tag])
    screen_context.result = first
    assert first.is_success() and second.is_success()
    assert first.result is not None and second.result is not None
    screen_context.csvs = [render_csv(first.result), render_csv(second.result)]


@when(parsers.parse('I screen in mode "{mode}"'))
def screen_mode(screen_context, mode):
    screen_context.result = _screen(screen_context, mode=mode)


def _payload(screen_context):
    result = screen_context.result
    assert result.is_success()
    assert result.result is not None
    return result.result


def _rows(screen_context):
    return _payload(screen_context).rows


@then(parsers.parse("the screen succeeds with {count:d} ranked rows"))
def screen_row_count(screen_context, count):
    assert_that(len(_rows(screen_context)), equal_to(count))


@then(parsers.parse('"{better}" ranks above "{worse}"'))
def rank_order(screen_context, better, worse):
    order = [row.symbol for row in _rows(screen_context)]
    assert_that(order.index(better) < order.index(worse), equal_to(True))


@then("every row has last_date on or before as-of")
def rows_within_as_of(screen_context):
    for row in _rows(screen_context):
        assert_that(row.last_date, less_than_or_equal_to(screen_context.as_of))


@then("data vintage equals as-of")
def vintage_equals_as_of(screen_context):
    assert_that(
        _payload(screen_context).data_vintage,
        equal_to(screen_context.as_of),
    )


@then(parsers.parse('exclusions report "{reason}"'))
def exclusions_report(screen_context, reason):
    assert_that(_payload(screen_context).excluded, has_key(reason))


@then("both CSV renders are identical")
def csv_deterministic(screen_context):
    assert_that(screen_context.csvs[0], equal_to(screen_context.csvs[1]))


@then(parsers.parse('the screen fails naming "{text}"'))
def screen_fails(screen_context, text):
    assert_that(screen_context.result.is_success(), equal_to(False))
    assert_that("; ".join(screen_context.result.errors), contains_string(text))


@then(parsers.parse('the rows are exactly "{first}" and "{second}"'))
def rows_exactly(screen_context, first, second):
    assert_that(
        sorted(row.symbol for row in _rows(screen_context)),
        equal_to([first, second]),
    )


@then("data vintage equals the full-universe vintage")
def vintage_full_universe(screen_context):
    assert_that(len(screen_context.full.rows) > 1, equal_to(True))
    assert_that(len(_rows(screen_context)), equal_to(1))
    assert_that(
        _payload(screen_context).data_vintage,
        equal_to(screen_context.full.data_vintage),
    )


@then(parsers.parse('the CSV header echoes "{text}"'))
def csv_echoes(screen_context, text):
    assert_that(render_csv(_payload(screen_context)), contains_string(text))


@then("scores descend with symbol tiebreak")
def scores_ordered(screen_context):
    rows = _rows(screen_context)
    scores = [row.score for row in rows]
    assert_that(scores, equal_to(sorted(scores, reverse=True)))
    assert_that(rows[0].rank, equal_to(1))


@then("the CSV header reports current membership vintage")
def membership_vintage(screen_context):
    assert_that(
        render_csv(_payload(screen_context)),
        contains_string("universe_membership_vintage=current"),
    )
