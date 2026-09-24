"""BDD coverage for SignalsUseCase, driven directly (no CLI)."""

from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.command.signals_current import SignalsRequest, SignalsUseCase, render_csv

FEATURE = Path(__file__).parent.parent / "features" / "command" / "signals.feature"
scenarios(str(FEATURE))

START = date(2022, 1, 3)


@pytest.fixture
def signals_context():
    return SimpleNamespace(local=None, result=None)


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
                symbol=symbol, date=day, open=close, high=close * 1.005,
                low=close * 0.995, close=close, volume=100000.0,
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


@when(parsers.parse('I score strategy "{strategy}" on tag "{tag}"'))
def score_strategy(signals_context, strategy, tag):
    signals_context.result = SignalsUseCase(signals_context.local).execute(
        SignalsRequest(include_tags=[tag], strategy_name=strategy)
    )


@when(parsers.parse('I score strategy "{strategy}" with momentum_top_share {share:f} on tag "{tag}"'))
def score_trend_pullback(signals_context, strategy, share, tag):
    signals_context.result = SignalsUseCase(signals_context.local).execute(
        SignalsRequest(
            include_tags=[tag], strategy_name=strategy,
            params={"momentum_top_share": str(share)},
        )
    )


@when(parsers.parse('I score strategy "{strategy}" on tag "{tag}" with benchmark "{benchmark}"'))
def score_with_benchmark(signals_context, strategy, tag, benchmark):
    signals_context.result = SignalsUseCase(signals_context.local).execute(
        SignalsRequest(include_tags=[tag], strategy_name=strategy, benchmark_symbol=benchmark)
    )


@then("every row has a signal date on or before as-of")
def rows_within_as_of(signals_context):
    for row in signals_context.result.rows:
        assert row.signal_date <= signals_context.result.as_of


@then("row \"AAA\" reports dist_lo, drawdown, and trend state")
def aaa_rank_inputs(signals_context):
    by_symbol = {row.symbol: row for row in signals_context.result.rows}
    aaa = by_symbol["AAA"]
    assert aaa.dist_lo is not None
    assert aaa.drawdown is not None
    assert aaa.above_fast is not None
    assert aaa.above_slow is not None


@then("the CSV states no fill price is shown or implied")
def no_fill_implied(signals_context):
    assert "no fill price is shown or implied" in render_csv(signals_context.result)


@then("every row reports momentum value, momentum rank, and gate")
def momentum_inputs(signals_context):
    for row in signals_context.result.rows:
        assert row.mom_value is not None
        assert row.mom_rank is not None
        assert row.gate is not None


@when(parsers.parse('I score strategy "{strategy}" on tag "{tag}" with benchmark "{benchmark}" included'))
def score_with_benchmark_included(signals_context, strategy, tag, benchmark):
    signals_context.result = SignalsUseCase(signals_context.local).execute(
        SignalsRequest(
            include_tags=[tag], strategy_name=strategy,
            benchmark_symbol=benchmark, include_benchmark=True,
        )
    )


@then(parsers.parse('"{symbol}" is a scored row'))
def is_scored(signals_context, symbol):
    assert symbol in {row.symbol for row in signals_context.result.rows}


@then("every non-empty numeric cell parses as float")
def numerics_parse(signals_context):
    import csv

    text = render_csv(signals_context.result)
    rows = list(csv.DictReader(filter(lambda line: not line.startswith("#"), text.splitlines())))
    assert rows, "expected at least one signal row"
    numeric = {
        "close", "last_entry_close", "last_exit_close", "dist_lo", "drawdown",
        "vov_pct", "mom_value", "mom_rank", "pullback_dist",
    }
    seen = 0
    for row in rows:
        for column in numeric:
            if row[column]:
                float(row[column])
                seen += 1
    assert seen > 0


@then(parsers.parse('"{symbol}" is not a scored row'))
def not_scored(signals_context, symbol):
    assert symbol not in {row.symbol for row in signals_context.result.rows}


@then("the CSV reports the benchmark resolved")
def benchmark_resolved(signals_context):
    assert signals_context.result.benchmark_resolved is True
    assert "(resolved)" in render_csv(signals_context.result)


@then("the CSV reports the benchmark missing with fallback")
def benchmark_missing(signals_context):
    assert signals_context.result.benchmark_resolved is False
    assert "missing;" in render_csv(signals_context.result)
