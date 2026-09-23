"""Unit tests for the SmaCrossStrategy golden-cross strategy."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import SmaCrossStrategy, StrategyRunner


def frame_from_closes(closes):
    idx = pd.date_range("2020-01-01", periods=len(closes), freq="B")
    closes = np.array(closes, float)
    return (
        pd.DataFrame({"A": closes}, index=idx),
        pd.DataFrame({"A": closes * 1.01}, index=idx),
        pd.DataFrame({"A": closes * 0.99}, index=idx),
    )


def rise_then_fall(n=400, flat=100, up=150):
    base = [100.0] * flat
    top = base[-1]
    climb = [top * (1.003**i) for i in range(1, up + 1)]
    peak = climb[-1]
    slide = [peak * (0.997**i) for i in range(1, n - flat - up + 1)]
    return base + climb + slide


class TestSmaCrossStrategy(unittest.TestCase):
    def test_cross_up_then_down_makes_one_round_trip(self):
        close, high, low = frame_from_closes(rise_then_fall())
        strategy = SmaCrossStrategy(fast_period=20, slow_period=50)

        signals = strategy.generate(close, high, low)
        assert_that(int(signals.entries.sum().sum()), equal_to(1))
        assert_that(int(signals.exits.sum().sum()), equal_to(1))
        result = StrategyRunner().run(strategy, close, high, low, start=close.index[0])

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.trades[0].gross_return > 0, equal_to(True))

    def test_flat_prices_never_cross(self):
        close, high, low = frame_from_closes([50.0] * 400)
        strategy = SmaCrossStrategy(fast_period=20, slow_period=50)

        assert_that(int(strategy.generate(close, high, low).entries.sum().sum()), equal_to(0))
        assert_that(StrategyRunner().run(strategy, close, high, low).n_trades, equal_to(0))

    def test_rejects_bad_periods(self):
        with self.assertRaises(ValueError):
            SmaCrossStrategy(fast_period=200, slow_period=50)
        with self.assertRaises(ValueError):
            SmaCrossStrategy(fast_period=50, slow_period=50)
        with self.assertRaises(ValueError):
            SmaCrossStrategy(fast_period=0, slow_period=50)

    def test_describe_mentions_periods(self):
        text = SmaCrossStrategy(fast_period=20, slow_period=50).describe()

        assert_that("20D" in text, equal_to(True))
        assert_that("50D" in text, equal_to(True))
