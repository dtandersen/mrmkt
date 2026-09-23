"""Unit tests for chunked execution and float32 precision parity."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, close_to, equal_to

from mrmkt.backtest.portfolio import aggregate_trades
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

    def test_fees_reduce_expectancy_exactly_once(self):
        close, high, low = universe_frames()
        strategy = BuyRedStrategy.trend_only()
        free = StrategyRunner(fees=0.0).run(strategy, close, high, low)
        paid = StrategyRunner(fees=0.001).run(strategy, close, high, low)

        assert_that(paid.n_trades >= 1, equal_to(True))
        assert_that(paid.n_trades, equal_to(free.n_trades))
        assert_that(free.expectancy - paid.expectancy, close_to(0.002, 1e-12))
        assert_that(paid.total_return < free.total_return, equal_to(True))

    def test_stop_uses_intrabar_low(self):
        closes = noisy_dip()
        idx = pd.date_range("2020-01-01", periods=len(closes), freq="B")
        arr = np.array(closes, float)
        crash = 335
        prev = arr[crash - 1]
        arr[crash] = prev * 0.98
        scale = arr[crash] / closes[crash]
        arr[crash + 1 :] *= scale
        close = pd.DataFrame({"A": arr}, index=idx)
        high = pd.DataFrame({"A": arr * 1.005}, index=idx)
        low = pd.DataFrame({"A": arr * 0.995}, index=idx)
        high.iloc[crash, 0] = prev * 1.005
        low.iloc[crash, 0] = prev * 0.80

        result = StrategyRunner().run(BuyRedStrategy.trend_only(), close, high, low)
        crash_day = idx[crash]
        stopped = [
            t for t in result.trades
            if t.exit_date == crash_day and t.gross_return < -0.05
        ]

        assert_that(len(stopped) >= 1, equal_to(True))

    def test_exit_day_counts_open_position(self):
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 105.0, 110.0, 115.0, 120.0], "B": [200.0] * 5}, index=idx)
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[0],
                    "Exit Timestamp": idx[2],
                    "Status": "Closed",
                    "Avg Entry Price": 100.0,
                    "Avg Exit Price": 110.0,
                    "Column": "A",
                },
                {
                    "Entry Timestamp": idx[1],
                    "Exit Timestamp": idx[3],
                    "Status": "Closed",
                    "Avg Entry Price": 200.0,
                    "Avg Exit Price": 200.0,
                    "Column": "B",
                },
            ]
        )

        result = aggregate_trades(close, records, max_positions=10)

        assert_that(result.n_trades, equal_to(2))
        assert_that(result.total_return, close_to(0.075, 1e-12))
