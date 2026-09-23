"""Unit tests for chunked execution and float32 precision parity."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import BuyRedStrategy, StrategyRunner


def noisy_dip(seed=42, n=400, dip_day=320, dip=(-0.04, -0.03)):
    rng = np.random.default_rng(seed)
    drift = np.full(n, 0.002) + rng.normal(0, 0.003, n)
    drift[dip_day + 1 : dip_day + 1 + len(dip)] = dip
    tail = dip_day + 1 + len(dip)
    drift[tail:] = 0.005 + rng.normal(0, 0.003, n - tail)
    return (100.0 * np.cumprod(1 + drift)).tolist()


def frames_for(symbols_closes):
    idx = pd.date_range("2020-01-01", periods=len(next(iter(symbols_closes.values()))), freq="B")
    closes, highs, lows = {}, {}, {}
    for sym, closes_list in symbols_closes.items():
        arr = np.array(closes_list, float)
        closes[sym] = pd.Series(arr, index=idx)
        highs[sym] = pd.Series(arr * 1.005, index=idx)
        lows[sym] = pd.Series(arr * 0.995, index=idx)
    return (
        pd.DataFrame(closes).sort_index(),
        pd.DataFrame(highs).sort_index(),
        pd.DataFrame(lows).sort_index(),
    )


def universe_frames():
    return frames_for(
        {
            "A": noisy_dip(),
            "B": [50.0] * 400,
            "C": (80.0 * np.cumprod(1 + np.full(400, 0.001))).tolist(),
        }
    )


class TestChunkedRunner(unittest.TestCase):
    def test_chunked_matches_single_run(self):
        close, high, low = universe_frames()
        strategy = BuyRedStrategy.trend_only()
        runner = StrategyRunner()
        chunk_a = (
            close[["A", "B"]],
            high[["A", "B"]],
            low[["A", "B"]],
        )
        chunk_b = (
            close[["C"]],
            high[["C"]],
            low[["C"]],
        )

        whole = runner.run(strategy, close, high, low)
        chunked = runner.run_chunked(strategy, [chunk_a, chunk_b])

        assert_that(chunked.n_trades, equal_to(whole.n_trades))
        assert_that(chunked.total_return, equal_to(whole.total_return))
        assert_that(chunked.expectancy, equal_to(whole.expectancy))

    def test_float32_matches_float64(self):
        close, high, low = universe_frames()
        strategy = BuyRedStrategy.trend_only()
        runner = StrategyRunner()

        base = runner.run(strategy, close, high, low)
        narrow = runner.run(
            strategy,
            close.astype(np.float32),
            high.astype(np.float32),
            low.astype(np.float32),
        )

        assert_that(narrow.n_trades, equal_to(base.n_trades))
        assert_that(narrow.total_return, equal_to(base.total_return))

    def test_empty_chunk_is_skipped(self):
        close, high, low = universe_frames()
        strategy = BuyRedStrategy.trend_only()
        runner = StrategyRunner()
        empty = (
            close[[]],
            high[[]],
            low[[]],
        )

        result = runner.run_chunked(strategy, [empty, (close, high, low)])
        expected = runner.run(strategy, close, high, low)

        assert_that(result.n_trades, equal_to(expected.n_trades))

    def test_all_empty_chunks_raise(self):
        close, high, low = universe_frames()
        empty = (
            close[[]],
            high[[]],
            low[[]],
        )

        with self.assertRaises(ValueError):
            StrategyRunner().run_chunked(BuyRedStrategy.trend_only(), [empty])
