"""Unit tests for current-signal discovery and the freshness report."""

import csv
import unittest
from datetime import date, timedelta

from hamcrest import assert_that, equal_to

from mrmkt.common.inmemfinrepo import InMemoryFinancialRepository
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.freshness import FreshnessRequest, FreshnessUseCase, render_csv as render_freshness
from mrmkt.usecase.signals_current import (
    SignalsRequest,
    SignalsUseCase,
    render_csv as render_signals,
)

START = date(2022, 1, 3)


def business_days(start: date, n: int) -> list:
    days = []
    current = start
    while len(days) < n:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


def add_series(repo, symbol, closes, exchange="NASDAQ", volume=100000.0, tag="universe"):
    repo.add_ticker(Ticker(ticker=symbol, exchange=exchange, type="us_equity"))
    for day, close in zip(business_days(START, len(closes)), closes, strict=True):
        repo.add_price(
            StockPrice(
                symbol=symbol,
                date=day,
                open=close,
                high=close * 1.005,
                low=close * 0.995,
                close=close,
                volume=volume,
            )
        )
    repo.add_tag(symbol, exchange, tag)


def climb(n=300, start=100.0, drift=0.002):
    closes = [start]
    for _ in range(1, n):
        closes.append(closes[-1] * (1 + drift))
    return closes


class TestSignalsCurrent(unittest.TestCase):
    def test_buy_red_rows_carry_rank_inputs(self):
        repo = InMemoryFinancialRepository()
        add_series(repo, "AAA", climb())
        add_series(repo, "BBB", climb(drift=0.0005))

        result = SignalsUseCase(repo).execute(
            SignalsRequest(include_tags=["universe"], strategy_name="buy-red")
        )

        by_symbol = {r.symbol: r for r in result.rows}
        assert_that(set(by_symbol), equal_to({"AAA", "BBB"}))
        for row in by_symbol.values():
            assert_that(row.signal_date <= result.as_of, equal_to(True))
            assert_that(row.status in ("entry_signal", "exit_signal", "neutral"), equal_to(True))
        aaa = by_symbol["AAA"]
        assert_that(aaa.dist_lo is not None, equal_to(True))
        assert_that(aaa.drawdown is not None, equal_to(True))
        assert_that(aaa.above_fast is not None, equal_to(True))
        assert_that(aaa.above_slow is not None, equal_to(True))

    def test_trend_pullback_rows_carry_candidate_rank_inputs(self):
        repo = InMemoryFinancialRepository()
        add_series(repo, "AAA", climb())
        add_series(repo, "BBB", climb(drift=0.0005))

        result = SignalsUseCase(repo).execute(
            SignalsRequest(
                include_tags=["universe"],
                strategy_name="trend-pullback",
                params={"momentum_top_share": "1.0"},
            )
        )

        for row in result.rows:
            assert_that(row.mom_value is not None, equal_to(True))
            assert_that(row.mom_rank is not None, equal_to(True))
            assert_that(row.gate is not None, equal_to(True))

    def test_benchmark_excluded_from_universe_by_default(self):
        repo = InMemoryFinancialRepository()
        add_series(repo, "AAA", climb())
        add_series(repo, "SPY", climb(), exchange="ARCA", tag="universe")

        result = SignalsUseCase(repo).execute(
            SignalsRequest(
                include_tags=["universe"], strategy_name="sma-cross", benchmark_symbol="SPY"
            )
        )

        assert_that({r.symbol for r in result.rows}, equal_to({"AAA"}))
        assert_that(result.benchmark_symbol, equal_to("SPY"))
        assert_that(result.benchmark_resolved, equal_to(True))

    def test_benchmark_override_keeps_it_tradable(self):
        repo = InMemoryFinancialRepository()
        add_series(repo, "SPY", climb(), exchange="ARCA", tag="universe")

        result = SignalsUseCase(repo).execute(
            SignalsRequest(
                include_tags=["universe"],
                strategy_name="sma-cross",
                benchmark_symbol="SPY",
                include_benchmark=True,
            )
        )

        assert_that({r.symbol for r in result.rows}, equal_to({"SPY"}))

    def test_missing_benchmark_uses_fallback_transparently(self):
        repo = InMemoryFinancialRepository()
        add_series(repo, "AAA", climb())

        result = SignalsUseCase(repo).execute(
            SignalsRequest(
                include_tags=["universe"], strategy_name="sma-cross", benchmark_symbol="SPY"
            )
        )

        assert_that(result.benchmark_resolved, equal_to(False))
        text = render_signals(result)
        assert_that("# benchmark=SPY (missing;" in text, equal_to(True))

    def test_no_fill_price_is_implied(self):
        repo = InMemoryFinancialRepository()
        add_series(repo, "AAA", climb())

        text = render_signals(
            SignalsUseCase(repo).execute(SignalsRequest(include_tags=["universe"]))
        )

        assert_that("no fill price is shown or implied" in text, equal_to(True))
        assert_that("fill_price" not in text.replace("no fill price", ""), equal_to(True))

    def test_signal_csv_numeric_fields_parse_as_floats(self):
        repo = InMemoryFinancialRepository()
        flat = [100.0] * 30
        peak = 100.0 * (1.002**120)
        closes = flat + [100.0 * (1.002**i) for i in range(1, 121)]
        closes += [peak * (0.9985**i) for i in range(1, 101)]
        add_series(repo, "AAA", closes)

        result = SignalsUseCase(repo).execute(
            SignalsRequest(
                include_tags=["universe"],
                strategy_name="sma-cross",
                params={"fast_period": "5", "slow_period": "20"},
            )
        )
        text = render_signals(result)
        rows = list(
            csv.DictReader(line for line in text.splitlines() if not line.startswith("#"))
        )
        numeric = [
            "close",
            "last_entry_close",
            "last_exit_close",
            "dist_lo",
            "drawdown",
            "vov_pct",
            "mom_value",
            "mom_rank",
            "pullback_dist",
        ]
        seen_entry_close = False
        for row in rows:
            for column in numeric:
                if row[column] != "":
                    float(row[column])
            if row["last_entry_close"] != "":
                seen_entry_close = True
        assert_that(seen_entry_close, equal_to(True))


class TestFreshness(unittest.TestCase):
    def test_stale_and_gaps_flagged(self):
        repo = InMemoryFinancialRepository()
        days = business_days(START, 30)
        add_series(repo, "OLD", [100.0 + i for i in range(30)])
        today = days[-1] + timedelta(days=10)

        result = FreshnessUseCase(repo).execute(
            FreshnessRequest(include_tags=["universe"], today=today)
        )

        row = result.rows[0]
        assert_that(row.staleness_days, equal_to(10))
        assert_that("STALE" in row.flags, equal_to(True))

    def test_ohlc_violation_and_zero_volume_flagged(self):
        repo = InMemoryFinancialRepository()
        repo.add_ticker(Ticker(ticker="BAD", exchange="NASDAQ", type="us_equity"))
        days = business_days(START, 10)
        for pos, day in enumerate(days):
            repo.add_price(
                StockPrice(
                    symbol="BAD",
                    date=day,
                    open=50.0,
                    high=51.0 if pos else 49.0,
                    low=49.0,
                    close=50.0,
                    volume=0.0 if pos == 5 else 1000.0,
                )
            )
        repo.add_tag("BAD", "NASDAQ", "universe")

        result = FreshnessUseCase(repo).execute(
            FreshnessRequest(include_tags=["universe"], today=days[-1])
        )

        row = result.rows[0]
        assert_that("OHLC_VIOLATION" in row.flags, equal_to(True))
        assert_that("ZERO_VOLUME" in row.flags, equal_to(True))

    def test_gap_jump_is_labeled_heuristic(self):
        repo = InMemoryFinancialRepository()
        closes = [100.0] * 10 + [50.0] * 10
        add_series(repo, "GAP", closes)

        result = FreshnessUseCase(repo).execute(
            FreshnessRequest(include_tags=["universe"], today=business_days(START, 20)[-1])
        )

        row = result.rows[0]
        assert_that("GAP_JUMP_HEURISTIC" in row.flags, equal_to(True))
        text = render_freshness(result)
        assert_that("suspicion heuristics" in text, equal_to(True))
        assert_that("no adjustment" in text, equal_to(True))

    def test_symbols_without_bars_reported(self):
        repo = InMemoryFinancialRepository()
        repo.add_ticker(Ticker(ticker="EMPTY", exchange="NASDAQ", type="us_equity"))
        repo.add_tag("EMPTY", "NASDAQ", "universe")

        result = FreshnessUseCase(repo).execute(
            FreshnessRequest(include_tags=["universe"], today=date(2024, 1, 10))
        )

        assert_that(result.rows[0].flags, equal_to(["NO_BARS"]))
