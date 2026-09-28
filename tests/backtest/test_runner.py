"""Unit tests for chunked execution and float32 precision parity."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, close_to, equal_to

from mrmkt.backtest.portfolio import aggregate_trades
from mrmkt.backtest.strategy import BuyRedStrategy, StrategyRunner
from mrmkt.backtest.strategy.base import ParamSpec, SignalSet, Strategy


class SingleSignalStrategy(Strategy):
    """Test stub: one entry bar and one exit bar (positions, not dates)."""

    def __init__(self, entry_pos=1, exit_pos=3):
        self.entry_pos = entry_pos
        self.exit_pos = exit_pos

    @classmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        return {}

    def generate(self, close, high, low, context=None) -> SignalSet:
        entries = pd.DataFrame(False, index=close.index, columns=close.columns)
        exits = pd.DataFrame(False, index=close.index, columns=close.columns)
        entries.iloc[self.entry_pos, :] = True
        exits.iloc[self.exit_pos, :] = True
        return SignalSet(entries=entries, exits=exits)

    def describe(self) -> str:
        return "single test entry and exit"


def noisy_dip(seed=42, n=400, dip_day=320, dip=(-0.04, -0.03)):
    rng = np.random.default_rng(seed)
    drift = np.full(n, 0.002) + rng.normal(0, 0.003, n)
    drift[dip_day + 1 : dip_day + 1 + len(dip)] = dip
    tail = dip_day + 1 + len(dip)
    drift[tail:] = 0.005 + rng.normal(0, 0.003, n - tail)
    return (100.0 * np.cumprod(1 + drift)).tolist()


def frames_for(symbols_closes):
    idx = pd.date_range(
        "2020-01-01", periods=len(next(iter(symbols_closes.values()))), freq="B"
    )
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

    def test_lone_first_bar_trade_pays_both_fees_in_portfolio(self):
        # Regression: the entry fee was booked on the entry bar, where the
        # position is not counted open, so a lone first-bar trade dropped
        # it from total_return while expectancy subtracted both sides.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 105.0, 110.0, 115.0, 120.0]}, index=idx)
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
            ]
        )
        fee = 0.001

        result = aggregate_trades(close, records, max_positions=10, fees_per_side=fee)

        day1 = 105.0 / 100.0 - 1 - fee
        day2 = 110.0 / 105.0 - 1 - fee
        assert_that(result.n_trades, equal_to(1))
        assert_that(result.total_return, close_to((1 + day1) * (1 + day2) - 1, 1e-12))
        assert_that(result.expectancy, close_to(0.10 - 2 * fee, 1e-12))

    def test_overlapping_trade_fees_split_across_open_positions(self):
        # Each side's fee must dilute across exactly the positions open
        # that day, including the entering/exiting trade itself.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame(
            {
                "A": [100.0, 105.0, 110.0, 115.0, 120.0],
                "B": [200.0] * 5,
            },
            index=idx,
        )
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
        fee = 0.001

        result = aggregate_trades(close, records, max_positions=10, fees_per_side=fee)

        day1 = 105.0 / 100.0 - 1 - fee
        day2 = ((110.0 / 105.0 - 1) + 0.0) / 2 - (2 * fee) / 2
        day3 = 0.0 - fee
        assert_that(result.n_trades, equal_to(2))
        assert_that(
            result.total_return,
            close_to((1 + day1) * (1 + day2) * (1 + day3) - 1, 1e-12),
        )
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
            t
            for t in result.trades
            if t.exit_date == crash_day and t.gross_return < -0.05
        ]

        assert_that(len(stopped) >= 1, equal_to(True))

    def test_exit_day_counts_open_position(self):
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame(
            {"A": [100.0, 105.0, 110.0, 115.0, 120.0], "B": [200.0] * 5}, index=idx
        )
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

    def test_next_bar_execution_delays_fills_by_one_bar(self):
        # Signals are known at bar close; the default executable model
        # fills the next close, never the signal bar itself.
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        result = StrategyRunner().run(
            SingleSignalStrategy(entry_pos=1, exit_pos=3),
            close,
            high,
            low,
            start=idx[0],
        )

        assert_that(result.n_trades, equal_to(1))
        trade = result.trades[0]
        assert_that(trade.entry_date, equal_to(idx[2]))
        assert_that(trade.exit_date, equal_to(idx[4]))
        assert_that(trade.gross_return, close_to(104.0 / 102.0 - 1, 1e-9))

    def test_zero_lag_fills_at_signal_close(self):
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        result = StrategyRunner(fill_lag=0).run(
            SingleSignalStrategy(entry_pos=1, exit_pos=3),
            close,
            high,
            low,
            start=idx[0],
        )

        assert_that(result.n_trades, equal_to(1))
        trade = result.trades[0]
        assert_that(trade.entry_date, equal_to(idx[1]))
        assert_that(trade.exit_date, equal_to(idx[3]))

    def test_invalid_fill_lag_raises(self):
        with self.assertRaises(ValueError):
            StrategyRunner(fill_lag=2)

    def test_missing_bar_days_carry_no_mark_or_count(self):
        # A gap in stored prices must not NaN-poison the shared series:
        # the gap days contribute no mark and no open count, while trade
        # accounting (entry/exit prices) still books the round trip.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 105.0, np.nan, 115.0, 120.0]}, index=idx)
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[0],
                    "Exit Timestamp": idx[3],
                    "Status": "Closed",
                    "Avg Entry Price": 100.0,
                    "Avg Exit Price": 115.0,
                    "Column": "A",
                },
            ]
        )

        result = aggregate_trades(close, records, max_positions=10)

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.total_return, close_to(105.0 / 100.0 - 1, 1e-12))
        assert_that(result.expectancy, close_to(115.0 / 100.0 - 1, 1e-12))
