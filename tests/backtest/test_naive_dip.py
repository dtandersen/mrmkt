"""Unit tests for the naive-dip baseline (validation test 2 anchor)."""

import unittest

import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import StrategyRunner, build_strategy
from mrmkt.backtest.strategy.naive_dip import NaiveDipStrategy


def rising_with_dip():
    idx = pd.date_range("2020-01-01", periods=100, freq="B")
    prices = [100.0 + 0.2 * i for i in range(100)]
    prices[70] = prices[69] * 0.94
    for i in range(71, 80):
        prices[i] = prices[70] + 0.2 * (i - 70)
    close = pd.DataFrame({"A": prices}, index=idx)
    return (
        close,
        pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx),
        pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx),
    )


class TestNaiveDipStrategy(unittest.TestCase):
    def test_registers_by_name(self):
        strategy = build_strategy("naive-dip", {})

        assert_that(isinstance(strategy, NaiveDipStrategy), equal_to(True))
        assert isinstance(strategy, NaiveDipStrategy)
        assert_that(strategy.dip_pct, equal_to(0.05))
        assert_that("dip" in strategy.describe().lower(), equal_to(True))

    def test_dip_triggers_entry_and_hold_releases(self):
        close, high, low = rising_with_dip()
        # Rip far out of reach so the fixed hold is the only exit.
        strategy = build_strategy("naive-dip", {"rip_pct": "5.0"})

        result = StrategyRunner(fill_lag=0).run(
            strategy, close, high, low, start=close.index[0]
        )

        assert_that(result.n_trades >= 1, equal_to(True))
        assert_that(result.avg_hold_days <= 10.0, equal_to(True))

    def test_invalid_params_raise(self):
        with self.assertRaises(ValueError):
            build_strategy("naive-dip", {"dip_pct": "1.5"})
        with self.assertRaises(ValueError):
            build_strategy("naive-dip", {"hold_days": "0"})
