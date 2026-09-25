"""BDD coverage for CurrentSignals, driven directly (no CLI)."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from hamcrest import assert_that, contains_string, equal_to, not_none
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.command.signals_current import (
    CurrentSignals,
    CurrentSignalsRequest,
    render_csv,
)
from mrmkt.common.clock import ClockStub
from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker

FEATURE = Path(__file__).parent.parent / "features" / "command" / "signals.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


@pytest.fixture
def signals_context():
    clock = ClockStub()
    clock.set_time(date(2024, 6, 30))
    return SimpleNamespace(local=None, result=None, clock=clock)


def _business_days(start: date, n: int) -> list:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def _add_series(repo, symbol, closes, exchange="NASDAQ"):
    repo.add_ticker(Ticker(ticker=symbol, exchange=exchange, type="us_equity"))
    for day, close in zip(_business_days(START, len(closes)), closes, strict=True):
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=close,
                high=close * 1.005,
                low=close * 0.995,
                close=close,
                volume=100000.0,
            )
        )


def _climb(n=300, drift=0.002):
    closes = [100.0]
    for _ in range(1, n):
        closes.append(closes[-1] * (1 + drift))
    return closes


@given("a clean price catalog")
def clean_catalog(signals_context):
    signals_context.local = InMemoryFinancialRepository()


@given(parsers.parse('symbol "{symbol}" has a 300-bar climb tagged "{tag}"'))
def symbol_has_climb(signals_context, symbol, tag):
    exchange = "ARCA" if symbol == "SPY" else "NASDAQ"
    _add_series(signals_context.local, symbol, _climb(), exchange=exchange)
    signals_context.local.add_tag(symbol, exchange, tag)


@given(parsers.parse('symbol "{symbol}" has a 300-bar flat line tagged "{tag}"'))
def symbol_has_flat(signals_context, symbol, tag):
    _add_series(signals_context.local, symbol, [50.0] * 300)
    signals_context.local.add_tag(symbol, "NASDAQ", tag)


def _score(signals_context, **kwargs):
    command = CurrentSignals(signals_context.local, signals_context.clock)
    return command.execute(CurrentSignalsRequest(**kwargs))


def _payload(signals_context):
    result = signals_context.result
    assert result.is_success()
    assert result.result is not None
    return result.result


@when(parsers.parse('I score strategy "{strategy}" on tag "{tag}"'))
def score_strategy(signals_context, strategy, tag):
    signals_context.result = _score(signals_context, tags=[tag], strategy_name=strategy)


@when(
    parsers.parse(
        'I score strategy "{strategy}" with momentum_top_share {share:f} on tag "{tag}"'
    )
)
def score_trend_pullback(signals_context, strategy, share, tag):
    signals_context.result = _score(
        signals_context,
        tags=[tag],
        strategy_name=strategy,
        params_text=f"momentum_top_share={share}",
    )


@when(
    parsers.parse(
        'I score strategy "{strategy}" on tag "{tag}" with benchmark "{benchmark}"'
    )
)
def score_with_benchmark(signals_context, strategy, tag, benchmark):
    signals_context.result = _score(
        signals_context, tags=[tag], strategy_name=strategy, benchmark=benchmark
    )


@when(
    parsers.parse(
        'I score strategy "{strategy}" on tag "{tag}" with benchmark "{benchmark}" included'
    )
)
def score_with_benchmark_included(signals_context, strategy, tag, benchmark):
    signals_context.result = _score(
        signals_context,
        tags=[tag],
        strategy_name=strategy,
        benchmark=benchmark,
        include_benchmark=True,
    )


@then("every row has a signal date on or before as-of")
def rows_within_as_of(signals_context):
    payload = _payload(signals_context)
    for row in payload.rows:
        assert_that(row.signal_date <= payload.as_of, equal_to(True))


@then('row "AAA" reports dist_lo, drawdown, and trend state')
def aaa_rank_inputs(signals_context):
    by_symbol = {row.symbol: row for row in _payload(signals_context).rows}
    aaa = by_symbol["AAA"]
    assert_that(aaa.dist_lo, not_none())
    assert_that(aaa.drawdown, not_none())
    assert_that(aaa.above_fast, not_none())
    assert_that(aaa.above_slow, not_none())


@then("the CSV states no fill price is shown or implied")
def no_fill_implied(signals_context):
    assert_that(
        render_csv(_payload(signals_context)),
        contains_string("no fill price is shown or implied"),
    )


@then("every row reports momentum value, momentum rank, and gate")
def momentum_inputs(signals_context):
    for row in _payload(signals_context).rows:
        assert_that(row.mom_value, not_none())
        assert_that(row.mom_rank, not_none())
        assert_that(row.gate, not_none())


@then("every non-empty numeric cell parses as float")
def numerics_parse(signals_context):
    import csv

    text = render_csv(_payload(signals_context))
    rows = list(
        csv.DictReader(filter(lambda line: not line.startswith("#"), text.splitlines()))
    )
    numeric = {
        "close",
        "last_entry_close",
        "last_exit_close",
        "dist_lo",
        "drawdown",
        "vov_pct",
        "mom_value",
        "mom_rank",
        "pullback_dist",
    }
    seen = 0
    for row in rows:
        for column in numeric:
            if row[column]:
                float(row[column])
                seen += 1
    assert_that(seen > 0, equal_to(True))


@then(parsers.parse('"{symbol}" is a scored row'))
def is_scored(signals_context, symbol):
    assert_that(
        symbol in {row.symbol for row in _payload(signals_context).rows},
        equal_to(True),
    )


@then(parsers.parse('"{symbol}" is not a scored row'))
def not_scored(signals_context, symbol):
    assert_that(
        symbol in {row.symbol for row in _payload(signals_context).rows},
        equal_to(False),
    )


@then("the CSV reports the benchmark resolved")
def benchmark_resolved(signals_context):
    payload = _payload(signals_context)
    assert_that(payload.benchmark_resolved, equal_to(True))
    assert_that(render_csv(payload), contains_string("(resolved)"))


@then("the CSV reports the benchmark missing with fallback")
def benchmark_missing(signals_context):
    payload = _payload(signals_context)
    assert_that(payload.benchmark_resolved, equal_to(False))
    assert_that(render_csv(payload), contains_string("missing;"))
