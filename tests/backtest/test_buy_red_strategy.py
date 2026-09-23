"""Unit tests for the BuyRedStrategy encapsulation."""

import unittest
from datetime import date

import numpy as np
import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import BuyRedStrategy, StrategyRunner


def frame_from_closes(closes):
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="B")
    closes = np.array(closes, float)
    return (
        pd.DataFrame({"A": closes}, index=idx),
        pd.DataFrame({"A": closes * 1.01}, index=idx),
        pd.DataFrame({"A": closes * 0.99}, index=idx),
    )


def v_dip(n=400, dip_day=320, dip=(-0.04, -0.03)):
    rng = np.random.default_rng(42)
    drift = np.full(n, 0.002) + rng.normal(0, 0.003, n)
    drift[dip_day + 1 : dip_day + 1 + len(dip)] = dip
    tail = dip_day + 1 + len(dip)
    drift[tail:] = 0.005 + rng.normal(0, 0.003, n - tail)
    return (100.0 * np.cumprod(1 + drift)).tolist()


class TestBuyRedStrategy(unittest.TestCase):
    def test_variants_differ_only_by_vov_filter(self):
        close, high, low = frame_from_closes(v_dip())
        plain = BuyRedStrategy.trend_only()
        compressed = BuyRedStrategy.with_compression()

        assert_that(plain.params.use_vov, equal_to(False))
        assert_that(compressed.params.use_vov, equal_to(True))
        assert_that(
            int(compressed.generate(close, high, low).entries.sum().sum())
            <= int(plain.generate(close, high, low).entries.sum().sum()),
            equal_to(True),
        )

    def test_backtest_completes_a_profitable_round_trip(self):
        close, high, low = frame_from_closes(v_dip())
        strategy = BuyRedStrategy.trend_only()
        runner = StrategyRunner()

        first = runner.run(strategy, close, high, low)
        second = runner.run(strategy, close, high, low)

        assert_that(first.n_trades >= 1, equal_to(True))
        assert_that(first.win_rate, equal_to(1.0))
        assert_that(first.expectancy > 0, equal_to(True))
        assert_that(second.total_return, equal_to(first.total_return))

    def test_compression_filter_rejects_vol_explosion(self):
        close, high, low = frame_from_closes(v_dip())

        assert_that(
            StrategyRunner().run(BuyRedStrategy.with_compression(), close, high, low).n_trades,
            equal_to(0),
        )

    def test_explicit_start_slices_the_window(self):
        close, high, low = frame_from_closes(v_dip())
        strategy = BuyRedStrategy.with_compression()
        runner = StrategyRunner()

        full = runner.run(strategy, close, high, low)
        late = runner.run(strategy, close, high, low, start=date(2021, 6, 1))

        assert_that(late.n_trades <= full.n_trades, equal_to(True))

    def test_describe_mentions_rules(self):
        text = BuyRedStrategy.with_compression().describe()

        assert_that("63D" in text, equal_to(True))
        assert_that("VoV" in text, equal_to(True))
