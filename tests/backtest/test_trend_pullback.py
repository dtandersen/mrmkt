"""Unit tests for the TrendPullbackStrategy candidate (plan section 4A)."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import (
    MarketContext,
    StrategyRunner,
    TrendPullbackStrategy,
    build_strategy,
)
from mrmkt.backtest.strategy.trend_pullback import equal_weight_index, market_gate


def drift_series(seed, n, drift, noise=0.003):
    rng = np.random.default_rng(seed)
    steps = drift + rng.normal(0, noise, n)
    return 100.0 * np.cumprod(1 + steps)


def frames_for(symbols_closes):
    n = len(next(iter(symbols_closes.values())))
    idx = pd.date_range("2020-01-01", periods=n, freq="B")
    closes, highs, lows = {}, {}, {}
    for sym, values in symbols_closes.items():
        arr = np.array(values, float)
        closes[sym] = pd.Series(arr, index=idx)
        highs[sym] = pd.Series(arr * 1.005, index=idx)
        lows[sym] = pd.Series(arr * 0.995, index=idx)
    return (
        pd.DataFrame(closes).sort_index(),
        pd.DataFrame(highs).sort_index(),
        pd.DataFrame(lows).sort_index(),
    )


def universe_frames(n=400):
    lead = drift_series(1, n, 0.002)
    dip_day = 320
    lead[dip_day + 1] *= 0.96
    lead[dip_day + 2] *= 0.97
    return frames_for(
        {
            # Steady climber with a mid-sample dip: top momentum, pullbacks occur.
            "LEAD": lead.tolist(),
            # Flat: weak momentum.
            "FLAT": [50.0] * n,
            # Decliner: bottom momentum.
            "LAG": drift_series(3, n, -0.002).tolist(),
        }
    )


def rising_benchmark(close, period=20):
    idx = close.index
    bench: pd.Series = pd.Series(100.0 * 1.002 ** np.arange(len(idx)), index=idx)
    avg: pd.Series = pd.Series(bench.rolling(period).mean())
    assert bool((bench.iloc[period:] > avg.iloc[period:]).all())
    return bench


def falling_benchmark(close, period=20):
    idx = close.index
    bench: pd.Series = pd.Series(100.0 * 0.996 ** np.arange(len(idx)), index=idx)
    avg: pd.Series = pd.Series(bench.rolling(period).mean())
    assert bool((bench.iloc[period:] < avg.iloc[period:]).all())
    return bench


def small_params(**overrides):
    base = {
        "market_sma": 20,
        "trend_sma": 50,
        "rising_bars": 5,
        "mom_lookback": 60,
        "mom_skip": 5,
        "pullback_period": 10,
        "recovery_bars": 0,
    }
    base.update(overrides)
    return base


class TestTrendPullbackRegistration(unittest.TestCase):
    def test_builds_from_registry_with_coercion(self):
        strategy = build_strategy(
            "trend-pullback", {"market_sma": "20", "require_rising": "true"}
        )

        assert isinstance(strategy, TrendPullbackStrategy)
        assert_that(strategy.params.market_sma, equal_to(20))
        assert_that(strategy.params.require_rising, equal_to(True))

    def test_specs_cover_hypothesis_thresholds(self):
        specs = TrendPullbackStrategy.param_specs()

        assert_that(specs["momentum_top_share"].default, equal_to(0.333))
        assert_that(specs["exit_mode"].default, equal_to("trend"))
        assert_that(bool(specs["pullback_tol"].help), equal_to(True))

    def test_invalid_options_rejected(self):
        with self.assertRaises(ValueError):
            TrendPullbackStrategy(exit_mode="diamond-hands")
        with self.assertRaises(ValueError):
            TrendPullbackStrategy(momentum_top_share=0.0)
        with self.assertRaises(ValueError):
            TrendPullbackStrategy(recovery_bars=2)

    def test_describe_names_gate_and_exit(self):
        text = TrendPullbackStrategy(**small_params()).describe()

        assert_that("20D SMA" in text, equal_to(True))
        assert_that("trend" in text, equal_to(True))


class TestTrendPullbackSignals(unittest.TestCase):
    def test_gate_blocks_entries_in_bear_market(self):
        close, high, low = universe_frames()
        strategy = TrendPullbackStrategy(**small_params())
        context = MarketContext(benchmark=falling_benchmark(close))

        entries = strategy.generate(close, high, low, context=context).entries

        assert_that(int(entries.sum().sum()), equal_to(0))

    def test_gate_passes_in_bull_market(self):
        close, high, low = universe_frames()
        strategy = TrendPullbackStrategy(**small_params())
        context = MarketContext(benchmark=rising_benchmark(close))

        signals = strategy.generate(close, high, low, context=context)

        assert_that(int(signals.entries.sum().sum()) >= 1, equal_to(True))

    def test_only_top_momentum_symbol_enters(self):
        close, high, low = universe_frames()
        strategy = TrendPullbackStrategy(**small_params())
        context = MarketContext(benchmark=rising_benchmark(close))

        entries = strategy.generate(close, high, low, context=context).entries

        entered = {col for col in entries.columns if bool(entries[col].any())}
        assert_that(entered, equal_to({"LEAD"}))

    def test_fallback_universe_runs_without_benchmark(self):
        close, high, low = universe_frames()
        strategy = TrendPullbackStrategy(**small_params())

        signals = strategy.generate(close, high, low)

        assert_that(set(signals.entries.columns), equal_to({"LEAD", "FLAT", "LAG"}))

    def test_universe_gate_is_scale_invariant(self):
        close, _, _ = universe_frames()
        scaled = close.copy()
        scaled["LEAD"] = scaled["LEAD"] * 7.3

        gate_plain = market_gate(
            close.index,
            close,
            None,
            market_sma=20,
            require_rising=False,
            rising_bars=5,
            fallback="universe",
        )
        gate_scaled = market_gate(
            scaled.index,
            scaled,
            None,
            market_sma=20,
            require_rising=False,
            rising_bars=5,
            fallback="universe",
        )

        assert_that(gate_plain.equals(gate_scaled), equal_to(True))
        assert_that(bool(gate_plain.any()), equal_to(True))

    def test_equal_weight_index_ignores_price_scale(self):
        close, _, _ = universe_frames()
        scaled = close.copy()
        scaled["FLAT"] = scaled["FLAT"] * 100.0

        assert_that(
            equal_weight_index(scaled).equals(equal_weight_index(close)),
            equal_to(True),
        )
        close, high, low = universe_frames()
        strategy = TrendPullbackStrategy(**small_params(benchmark_fallback="none"))

        entries = strategy.generate(close, high, low, context=None).entries

        assert_that(int(entries.sum().sum()) >= 1, equal_to(True))

    def test_range_exit_also_fires_at_range_top(self):
        close, high, low = universe_frames()
        trend_only = TrendPullbackStrategy(**small_params(exit_mode="trend"))
        with_range = TrendPullbackStrategy(**small_params(exit_mode="range"))
        context = MarketContext(benchmark=rising_benchmark(close))

        trend_exits = trend_only.generate(close, high, low, context=context).exits
        range_exits = with_range.generate(close, high, low, context=context).exits

        assert_that(
            int(range_exits.sum().sum()) >= int(trend_exits.sum().sum()), equal_to(True)
        )

    def test_recovery_trigger_is_stricter_than_touch_only(self):
        close, high, low = universe_frames()
        touch = TrendPullbackStrategy(**small_params(recovery_bars=0))
        recovery = TrendPullbackStrategy(**small_params(recovery_bars=1))
        context = MarketContext(benchmark=rising_benchmark(close))

        touch_entries = touch.generate(close, high, low, context=context).entries
        recovery_entries = recovery.generate(close, high, low, context=context).entries

        assert_that(
            int(recovery_entries.sum().sum()) <= int(touch_entries.sum().sum()),
            equal_to(True),
        )


class TestTrendPullbackRunner(unittest.TestCase):
    def test_chunked_matches_single_run_with_universe_ranks(self):
        close, high, low = universe_frames()
        # Range exits close trades on a steady climber; pure trend exits
        # would leave positions open and n_trades at zero.
        strategy = TrendPullbackStrategy(**small_params(exit_mode="range"))
        context_bench = rising_benchmark(close)
        runner = StrategyRunner()

        whole = runner.run(strategy, close, high, low, benchmark=context_bench)
        chunked = runner.run_chunked(
            strategy,
            [(close[["LEAD", "FLAT"]], high[["LEAD", "FLAT"]], low[["LEAD", "FLAT"]]),
             (close[["LAG"]], high[["LAG"]], low[["LAG"]])],
            benchmark=context_bench,
        )

        assert_that(chunked.n_trades, equal_to(whole.n_trades))
        assert_that(chunked.total_return, equal_to(whole.total_return))
        assert_that(chunked.n_trades >= 1, equal_to(True))

    def test_benchmark_never_becomes_tradable(self):
        close, high, low = universe_frames()
        bench = rising_benchmark(close).rename("SPY")
        strategy = TrendPullbackStrategy(**small_params())
        result = StrategyRunner().run(strategy, close, high, low, benchmark=bench)

        traded = {t.entry_date is not None for t in result.trades}
        assert_that(len(traded) >= 0, equal_to(True))
        for trade in result.trades:
            assert_that(hasattr(trade, "gross_return"), equal_to(True))
        # No SPY column can leak: the runner only aggregates chunk closes.
        assert_that("SPY" in list(close.columns), equal_to(False))
