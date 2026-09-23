"""Unit tests for the vectorbt backtest engine (signals + portfolio)."""

import unittest

import numpy as np
import pandas as pd
from hamcrest import assert_that, equal_to

from mrmkt.backtest.portfolio import run_portfolio
from mrmkt.backtest.signals import BacktestParams, entry_signals, exit_signals


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


class TestBacktestSignals(unittest.TestCase):
    def test_downtrend_produces_no_entries(self):
        closes = [100.0 * (0.995**i) for i in range(400)]
        close, _, low = frame_from_closes(closes)
        entries = entry_signals(close, low, BacktestParams())

        assert_that(entries.sum().sum(), equal_to(0))

    def test_flat_prices_produce_no_entries(self):
        close, _, low = frame_from_closes([50.0] * 400)
        entries = entry_signals(close, low, BacktestParams())

        assert_that(entries.sum().sum(), equal_to(0))

    def test_dip_in_uptrend_triggers_entry_and_exit(self):
        close, high, low = frame_from_closes(v_dip())
        params = BacktestParams()
        entries = entry_signals(close, low, params)
        exits = exit_signals(close, high, params)

        assert_that(int(entries.sum().sum()) >= 1, equal_to(True))
        first_entry = entries[entries["A"]].index[0]
        assert_that(
            bool((exits.loc[first_entry:]["A"]).any()),
            equal_to(True),
        )


class TestBacktestPortfolio(unittest.TestCase):
    def test_round_trip_produces_sane_statistics(self):
        close, high, low = frame_from_closes(v_dip())
        params = BacktestParams()
        entries = entry_signals(close, low, params)
        exits = exit_signals(close, high, params)
        result = run_portfolio(close, entries, exits)

        assert_that(result.n_trades >= 1, equal_to(True))
        assert_that(0.0 <= result.win_rate <= 1.0, equal_to(True))
        assert_that(abs(result.total_return) < 10.0, equal_to(True))
        again = run_portfolio(close, entries, exits)
        assert_that(again.total_return, equal_to(result.total_return))

    def test_no_signals_yields_empty_result(self):
        close, _, low = frame_from_closes([50.0] * 400)
        entries = entry_signals(close, low, BacktestParams())
        exits = exit_signals(
            close,
            pd.DataFrame({"A": [50.0] * 400}, index=close.index),
            BacktestParams(),
        )
        result = run_portfolio(close, entries, exits)

        assert_that(result.n_trades, equal_to(0))
        assert_that(result.total_return, equal_to(0.0))

    def test_misaligned_frames_are_rejected(self):
        close, _, low = frame_from_closes(v_dip())
        with self.assertRaises(ValueError):
            run_portfolio(close.iloc[:10], entry_signals(close, low, BacktestParams()),
                           exit_signals(close, close, BacktestParams()))
