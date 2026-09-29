"""Unit tests for chunked execution and float32 precision parity."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, close_to, equal_to

from mrmkt.backtest.portfolio import aggregate_trades, run_portfolio
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

    def test_same_day_round_trip_books_gross_and_both_fees(self):
        # Same-bar entry+exit (e.g. an intrabar stop) has no
        # close-to-close marks. The fill prices plus both fees must land
        # on the entry day; previously the record vanished from the
        # equity curve AND the trade stats entirely.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 105.0, 110.0, 115.0, 120.0]}, index=idx)
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[1],
                    "Exit Timestamp": idx[1],
                    "Status": "Closed",
                    "Avg Entry Price": 105.0,
                    "Avg Exit Price": 100.0,
                    "Column": "A",
                },
            ]
        )
        fee = 0.001

        result = aggregate_trades(close, records, max_positions=10, fees_per_side=fee)

        day = 100.0 / 105.0 - 1 - 2 * fee
        assert_that(result.n_trades, equal_to(1))
        assert_that(result.total_return, close_to(day, 1e-12))
        assert_that(result.expectancy, close_to(100.0 / 105.0 - 1 - 2 * fee, 1e-12))
        assert_that(result.trades[0].hold_days, equal_to(0))
        assert_that(result.win_rate, equal_to(0.0))

    def test_position_opened_on_last_bar_books_entry_fee(self):
        # No subsequent bars exist for marks, but the entry fee was paid
        # and must not disappear from the equity curve.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 105.0, 110.0, 115.0, 120.0]}, index=idx)
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[4],
                    "Exit Timestamp": pd.NaT,
                    "Status": "Open",
                    "Avg Entry Price": 120.0,
                    "Avg Exit Price": np.nan,
                    "Column": "A",
                },
            ]
        )
        fee = 0.001

        result = aggregate_trades(close, records, max_positions=10, fees_per_side=fee)

        assert_that(result.n_trades, equal_to(0))
        assert_that(result.total_return, close_to(-fee, 1e-12))

    def test_limit_touch_fills_only_touched_limits(self):
        # Resting limits known at the signal close fill only when the
        # fill bar's low reaches them; missed limits simply do not fill.
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        class TouchStub(SingleSignalStrategy):
            def generate(self, close, high, low, context=None):
                signals = super().generate(close, high, low, context)
                signals.entries.iloc[3, :] = True
                return signals

            def entry_limits(self, close, high, low, context=None):
                # Signal bars are 1 and 3; fill bars 2 and 4. Touch the
                # first limit, miss the second.
                limits = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
                limits.iloc[1, :] = 1000.0
                limits.iloc[3, :] = 1.0
                return limits

        strategy = TouchStub(entry_pos=1, exit_pos=4)
        result = StrategyRunner(fill_model="limit-touch").run(
            strategy, close, high, low, start=idx[0]
        )

        assert_that(result.n_trades, equal_to(1))

    def test_limit_touch_nan_limit_is_a_market_entry(self):
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        class MarketStub(SingleSignalStrategy):
            def entry_limits(self, close, high, low, context=None):
                return pd.DataFrame(np.nan, index=close.index, columns=close.columns)

        result = StrategyRunner(fill_model="limit-touch").run(
            MarketStub(entry_pos=1, exit_pos=3), close, high, low, start=idx[0]
        )

        assert_that(result.n_trades, equal_to(1))

    def test_limit_touch_without_limits_is_rejected(self):
        close, high, low = universe_frames()

        with self.assertRaises(ValueError):
            StrategyRunner(fill_model="limit-touch").run(
                SingleSignalStrategy(), close, high, low
            )

    def test_unknown_fill_model_is_rejected(self):
        with self.assertRaises(ValueError):
            StrategyRunner(fill_model="midpoint")

    def test_unknown_fill_price_is_rejected(self):
        with self.assertRaises(ValueError):
            StrategyRunner(fill_price="midpoint")

    def test_limit_fill_price_needs_limit_touch_model(self):
        with self.assertRaises(ValueError):
            StrategyRunner(fill_model="close", fill_price="limit")

    def test_limit_fill_price_uses_resting_limit(self):
        # The resting limit (103.50) is below the fill-bar close (104):
        # economics must compound from what the order actually gets.
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 104.0, 106.0, 108.0, 110.0, 112.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        class LimitPriceStub(SingleSignalStrategy):
            def entry_limits(self, close, high, low, context=None):
                limits = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
                limits.iloc[0, :] = 103.5
                return limits

        result = StrategyRunner(fill_model="limit-touch", fill_price="limit").run(
            LimitPriceStub(entry_pos=0, exit_pos=2), close, high, low, start=idx[0]
        )
        baseline = StrategyRunner(fill_model="limit-touch").run(
            LimitPriceStub(entry_pos=0, exit_pos=2), close, high, low, start=idx[0]
        )

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.expectancy, close_to(108.0 / 103.5 - 1, 1e-6))
        assert_that(result.total_return, close_to(108.0 / 103.5 - 1, 1e-6))
        assert_that(result.expectancy > baseline.expectancy, equal_to(True))

    def test_stop_anchors_to_limit_fill_not_close_fill(self):
        # Reviewer repro: limit 90 touched on a fill bar closing at 100.
        # A real 90 fill stops at 82.8 and survives the 91-low bar; the old
        # map-only overlay stopped at 92 off the close fill and reported
        # a +2.22% winner. Must headline -8%.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 100.0, 95.0, 98.0, 99.0]}, index=idx)
        high = pd.DataFrame({"A": [101.0, 101.0, 96.0, 99.0, 100.0]}, index=idx)
        low = pd.DataFrame({"A": [99.0, 89.0, 91.0, 79.0, 98.0]}, index=idx)

        class StopBasisStub(SingleSignalStrategy):
            def entry_limits(self, close, high, low, context=None):
                limits = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
                limits.iloc[0, :] = 90.0
                return limits

        result = StrategyRunner(
            fill_model="limit-touch", fill_price="limit", stop=0.08
        ).run(StopBasisStub(entry_pos=0, exit_pos=4), close, high, low, start=idx[0])

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.expectancy, close_to(-0.08, 1e-6))
        assert_that(result.total_return, close_to(-0.08, 1e-6))
        assert_that(result.max_drawdown < 0.0, equal_to(True))

    def test_stop_wins_ties_against_same_bar_exit(self):
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 100.0, 95.0, 98.0, 99.0]}, index=idx)
        high = pd.DataFrame({"A": [101.0, 101.0, 96.0, 99.0, 100.0]}, index=idx)
        low = pd.DataFrame({"A": [99.0, 89.0, 91.0, 79.0, 98.0]}, index=idx)

        class TieStub(SingleSignalStrategy):
            def entry_limits(self, close, high, low, context=None):
                limits = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
                limits.iloc[0, :] = 90.0
                return limits

        result = StrategyRunner(
            fill_model="limit-touch", fill_price="limit", stop=0.08
        ).run(TieStub(entry_pos=0, exit_pos=2), close, high, low, start=idx[0])

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.expectancy, close_to(-0.08, 1e-6))

    def test_entries_while_holding_are_ignored(self):
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        class PyramidStub(SingleSignalStrategy):
            def generate(self, close, high, low, context=None):
                signals = super().generate(close, high, low, context)
                signals.entries.iloc[1, :] = True
                return signals

            def entry_limits(self, close, high, low, context=None):
                limits = pd.DataFrame(np.nan, index=close.index, columns=close.columns)
                limits.iloc[0, :] = 100.6
                limits.iloc[1, :] = 101.6
                return limits

        result = StrategyRunner(fill_model="limit-touch", fill_price="limit").run(
            PyramidStub(entry_pos=0, exit_pos=4), close, high, low, start=idx[0]
        )

        # One trade at the FIRST fill (100.60), not the second (101.60).
        assert_that(result.n_trades, equal_to(1))
        assert_that(result.expectancy, close_to(105.0 / 100.6 - 1, 1e-6))

    def test_limit_fill_price_with_nan_limit_fills_at_close(self):
        idx = pd.date_range("2020-01-01", periods=6, freq="B")
        prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
        close = pd.DataFrame({"A": prices}, index=idx)
        high = pd.DataFrame({"A": [p * 1.005 for p in prices]}, index=idx)
        low = pd.DataFrame({"A": [p * 0.995 for p in prices]}, index=idx)

        class MarketStub(SingleSignalStrategy):
            def entry_limits(self, close, high, low, context=None):
                return pd.DataFrame(np.nan, index=close.index, columns=close.columns)

        result = StrategyRunner(fill_model="limit-touch", fill_price="limit").run(
            MarketStub(entry_pos=1, exit_pos=3), close, high, low, start=idx[0]
        )

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.expectancy, close_to(104.0 / 102.0 - 1, 1e-9))

    def test_negative_fees_rejected_at_runner(self):
        # The CLI blocks negative friction; the runner must too, since a
        # subsidy reports phantom gains (flat prices showed +2.01%).
        with self.assertRaises(ValueError):
            StrategyRunner(fees=-0.01)

    def test_negative_fees_rejected_at_public_entrypoints(self):
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0] * 5}, index=idx)
        entries = pd.DataFrame(False, index=idx, columns=["A"])
        exits = pd.DataFrame(False, index=idx, columns=["A"])
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[0],
                    "Exit Timestamp": idx[1],
                    "Status": "Closed",
                    "Avg Entry Price": 100.0,
                    "Avg Exit Price": 100.0,
                    "Column": "A",
                },
            ]
        )

        with self.assertRaises(ValueError):
            run_portfolio(close, entries, exits, fees=-0.01)
        with self.assertRaises(ValueError):
            aggregate_trades(close, records, max_positions=10, fees_per_side=-0.01)

    def test_invalid_stop_and_size_rejected_at_runner(self):
        with self.assertRaises(ValueError):
            StrategyRunner(stop=0.0)
        with self.assertRaises(ValueError):
            StrategyRunner(stop=1.0)
        with self.assertRaises(ValueError):
            StrategyRunner(size_pct=0.0)
        with self.assertRaises(ValueError):
            StrategyRunner(size_pct=101.0)

    def test_buy_red_limit_touch_trades_subset_of_close_fills(self):
        close, high, low = universe_frames()
        strategy = BuyRedStrategy.trend_only()
        traded = StrategyRunner(fill_model="limit-touch").run(
            strategy, close, high, low
        )
        filled = StrategyRunner(fill_model="close").run(strategy, close, high, low)

        assert_that(traded.n_trades >= 1, equal_to(True))
        assert_that(traded.n_trades <= filled.n_trades, equal_to(True))

    def test_exit_day_mark_uses_actual_exit_fill_not_close(self):
        # A position stopped out intrabar (-8%) whose close then recovered
        # (+10%) must headline as a loser on the equity curve, matching the
        # trade stats — not as a +10% winner with a flat drawdown.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 110.0, 115.0, 120.0, 125.0]}, index=idx)
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[0],
                    "Exit Timestamp": idx[1],
                    "Status": "Closed",
                    "Avg Entry Price": 100.0,
                    "Avg Exit Price": 92.0,
                    "Column": "A",
                },
            ]
        )
        fee = 0.001

        result = aggregate_trades(close, records, max_positions=10, fees_per_side=fee)

        day = 92.0 / 100.0 - 1 - 2 * fee
        assert_that(result.n_trades, equal_to(1))
        assert_that(result.total_return, close_to(day, 1e-12))
        assert_that(result.expectancy, close_to(92.0 / 100.0 - 1 - 2 * fee, 1e-12))
        assert_that(result.max_drawdown, close_to(day, 1e-12))
        assert_that(result.win_rate, equal_to(0.0))

    def test_gap_days_bridge_return_and_hold_the_cap_slot(self):
        # A gap in stored prices must not erase P/L: the valid-to-valid
        # change books when prices resume (matching the trade gross), and
        # the held position keeps consuming cap through the gap.
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

        day1 = 105.0 / 100.0 - 1
        day3 = 115.0 / 105.0 - 1
        assert_that(result.n_trades, equal_to(1))
        assert_that(result.total_return, close_to((1 + day1) * (1 + day3) - 1, 1e-12))
        assert_that(result.expectancy, close_to(115.0 / 100.0 - 1, 1e-12))
        assert_that(result.exposure, close_to(3 / 5, 1e-12))

    def test_gap_resume_down_books_the_loss(self):
        # Reverse the gap outcome: the slide from the last observed 105
        # to the 90 exit must headline, not vanish into the gap.
        idx = pd.date_range("2020-01-01", periods=5, freq="B")
        close = pd.DataFrame({"A": [100.0, 105.0, np.nan, 90.0, 95.0]}, index=idx)
        records = pd.DataFrame(
            [
                {
                    "Entry Timestamp": idx[0],
                    "Exit Timestamp": idx[3],
                    "Status": "Closed",
                    "Avg Entry Price": 100.0,
                    "Avg Exit Price": 90.0,
                    "Column": "A",
                },
            ]
        )

        result = aggregate_trades(close, records, max_positions=10)

        day1 = 105.0 / 100.0 - 1
        day3 = 90.0 / 105.0 - 1
        assert_that(result.n_trades, equal_to(1))
        assert_that(result.total_return, close_to((1 + day1) * (1 + day3) - 1, 1e-12))
        assert_that(result.expectancy, close_to(90.0 / 100.0 - 1, 1e-12))
        assert_that(result.win_rate, equal_to(0.0))

    def test_stop_on_missing_close_day_books_exit_pin(self):
        # Runner-level: an intrabar stop on a NaN-close bar still pins
        # its exit fill to the equity curve (not just the trade stats).
        idx = pd.date_range("2020-01-01", periods=4, freq="B")
        close = pd.DataFrame({"A": [100.0, 100.0, np.nan, 100.0]}, index=idx)
        high = pd.DataFrame({"A": [100.0, 101.0, 110.0, 101.0]}, index=idx)
        low = pd.DataFrame({"A": [99.0, 99.0, 90.0, 99.0]}, index=idx)

        result = StrategyRunner(stop=0.08).run(
            SingleSignalStrategy(entry_pos=0, exit_pos=3),
            close,
            high,
            low,
            start=idx[0],
        )

        assert_that(result.n_trades, equal_to(1))
        assert_that(result.expectancy, close_to(-0.08, 1e-6))
        assert_that(result.total_return, close_to(-0.08, 1e-6))
        assert_that(result.max_drawdown < 0.0, equal_to(True))

    def test_gap_day_keeps_its_cap_slot(self):
        # With one slot, a trade held through a gap blocks a second trade
        # that tries to open on the gap day itself.
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
                {
                    "Entry Timestamp": idx[2],
                    "Exit Timestamp": idx[4],
                    "Status": "Closed",
                    "Avg Entry Price": 115.0,
                    "Avg Exit Price": 120.0,
                    "Column": "A",
                },
            ]
        )

        result = aggregate_trades(close, records, max_positions=1)

        assert_that(result.n_trades, equal_to(1))
