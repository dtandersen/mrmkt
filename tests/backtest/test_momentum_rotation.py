"""Unit tests for the MomentumRotationStrategy comparator (plan section 4B)."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.strategy import (
    MarketContext,
    MomentumRotationStrategy,
    StrategyRunner,
    build_strategy,
)


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


def climber(seed, n, drift=0.002):
    rng = np.random.default_rng(seed)
    return 100.0 * np.cumprod(1 + drift + rng.normal(0, 0.003, n))


def rotation_frames(n=400):
    """LEAD leads the first half, CHASER the second; FLAT never leads."""
    first = climber(11, n // 2, 0.004)
    second = first[-1] * np.cumprod(1 + np.full(n - n // 2, 0.0005))
    lead = np.r_[first, second]
    slow_start = climber(22, n // 2, 0.0005)
    fast_tail = slow_start[-1] * np.cumprod(1 + np.full(n - n // 2, 0.004))
    chaser = np.r_[slow_start, fast_tail]
    return frames_for({"LEAD": lead, "CHASER": chaser, "FLAT": [50.0] * n})


def small_params(**overrides):
    base = {
        "mom_lookback": 60,
        "mom_skip": 5,
        "top_n": 1,
        "rebalance_days": 30,
        "market_sma": 20,
        "use_gate": False,
    }
    base.update(overrides)
    return base


def rising_benchmark(close, period=20):
    idx = close.index
    return pd.Series(100.0 * 1.002 ** np.arange(len(idx)), index=idx)


def falling_benchmark(close, period=20):
    idx = close.index
    bench: pd.Series = pd.Series(100.0 * 0.996 ** np.arange(len(idx)), index=idx)
    assert bool((bench.iloc[period:] < bench.rolling(period).mean().iloc[period:]).all())
    return bench


class TestMomentumRotationRegistration(unittest.TestCase):
    def test_builds_from_registry_with_coercion(self):
        strategy = build_strategy(
            "momentum-rotation", {"top_n": "3", "use_gate": "false"}
        )

        assert isinstance(strategy, MomentumRotationStrategy)
        assert_that(strategy.params.top_n, equal_to(3))
        assert_that(strategy.params.use_gate, equal_to(False))

    def test_specs_cover_hypothesis_thresholds(self):
        specs = MomentumRotationStrategy.param_specs()

        assert_that(specs["rebalance_days"].default, equal_to(21))
        assert_that(specs["top_n"].default, equal_to(20))
        assert_that(bool(specs["mom_skip"].help), equal_to(True))

    def test_invalid_options_rejected(self):
        with self.assertRaises(ValueError):
            MomentumRotationStrategy(top_n=0)
        with self.assertRaises(ValueError):
            MomentumRotationStrategy(mom_skip=60, mom_lookback=60)
        with self.assertRaises(ValueError):
            MomentumRotationStrategy(rebalance_days=0)

    def test_describe_names_schedule_and_regime(self):
        text = MomentumRotationStrategy(**small_params()).describe()

        assert_that("top 1" in text, equal_to(True))
        assert_that("30D" in text, equal_to(True))


class TestMomentumRotationSignals(unittest.TestCase):
    def test_holds_strongest_name(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        context = MarketContext(benchmark=rising_benchmark(close))

        entries = strategy.generate(close, high, low, context=context).entries

        first_entry = entries.index[entries.any(axis=1)][0]
        assert_that(bool(entries.loc[first_entry, "LEAD"]), equal_to(True))
        assert_that(bool(entries.loc[first_entry, "FLAT"]), equal_to(False))

    def test_leadership_change_rotates_holdings(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        context = MarketContext(benchmark=rising_benchmark(close))

        signals = strategy.generate(close, high, low, context=context)

        assert_that(bool(signals.entries["CHASER"].any()), equal_to(True))
        assert_that(bool(signals.exits["LEAD"].any()), equal_to(True))

    def test_entries_only_on_rebalance_dates(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        context = MarketContext(benchmark=rising_benchmark(close))

        entries = strategy.generate(close, high, low, context=context).entries
        entry_positions = [
            pos for pos, day in enumerate(entries.index) if bool(entries.iloc[pos].any())
        ]

        assert_that(all(pos % 30 == 0 for pos in entry_positions), equal_to(True))

    def test_gate_off_forces_cash(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params(use_gate=True))
        context = MarketContext(benchmark=falling_benchmark(close))

        entries = strategy.generate(close, high, low, context=context).entries

        assert_that(int(entries.sum().sum()), equal_to(0))

    def test_gate_can_be_disabled(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params(use_gate=False))
        context = MarketContext(benchmark=falling_benchmark(close))

        entries = strategy.generate(close, high, low, context=context).entries

        assert_that(int(entries.sum().sum()) >= 1, equal_to(True))

    def test_entries_and_exits_never_overlap(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        context = MarketContext(benchmark=rising_benchmark(close))

        signals = strategy.generate(close, high, low, context=context)

        assert_that(bool((signals.entries & signals.exits).any().any()), equal_to(False))

    def test_test_start_seeds_wanted_holdings(self):
        # LEAD leads the whole first half, so it is wanted on both
        # sides of a mid-half test start: the seed bar must carry an
        # entry even though the warm-up entry is later filtered out.
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        seed_day = pd.Timestamp(str(close.index[150]))
        context = MarketContext(
            benchmark=rising_benchmark(close), test_start=seed_day
        )

        entries = strategy.generate(close, high, low, context=context).entries

        assert_that(bool(entries.loc[seed_day, "LEAD"]), equal_to(True))


class TestMomentumRotationRunner(unittest.TestCase):
    def test_chunked_matches_single_run_with_universe_ranks(self):
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        bench = rising_benchmark(close)
        runner = StrategyRunner()
        # Rotation trades sparsely; start early so the test-window
        # filter keeps the entries while still exercising the path.
        start = close.index[55]

        whole = runner.run(strategy, close, high, low, start=start, benchmark=bench)
        chunked = runner.run_chunked(
            strategy,
            [
                (
                    close[["LEAD", "FLAT"]],
                    high[["LEAD", "FLAT"]],
                    low[["LEAD", "FLAT"]],
                ),
                (close[["CHASER"]], high[["CHASER"]], low[["CHASER"]]),
            ],
            benchmark=bench,
            start=start,
        )

        assert_that(chunked.n_trades, equal_to(whole.n_trades))
        assert_that(chunked.total_return, equal_to(whole.total_return))
        assert_that(chunked.n_trades >= 1, equal_to(True))

    def test_benchmark_never_becomes_tradable(self):
        close, high, low = rotation_frames()
        bench = rising_benchmark(close).rename("SPY")
        strategy = MomentumRotationStrategy(**small_params())
        result = StrategyRunner().run(
            strategy, close, high, low, start=close.index[55], benchmark=bench
        )

        assert_that("SPY" in list(close.columns), equal_to(False))
        assert_that(result.n_trades >= 1, equal_to(True))

    def test_runner_keeps_seeded_position_after_start(self):
        # Same top name wanted on both sides of the test start: without
        # seeding, the warm-up entry is filtered out and the portfolio
        # starts unintentionally in cash.
        close, high, low = rotation_frames()
        strategy = MomentumRotationStrategy(**small_params())
        bench = rising_benchmark(close)
        start = close.index[150]

        result = StrategyRunner().run(
            strategy, close, high, low, start=start, benchmark=bench
        )

        assert_that(result.n_trades >= 1, equal_to(True))
        assert_that(result.exposure > 0, equal_to(True))
