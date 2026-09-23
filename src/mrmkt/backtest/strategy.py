"""Vectorbt-backed trading strategies and the runner that executes them.

Strategies are pure signal definitions: parameters, ``generate()``, and
a human-readable ``describe()``. All execution lives in StrategyRunner,
which slices warm-up history and runs the vectorbt fill simulator with
an explicit portfolio overlay.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from mrmkt.backtest.portfolio import (
    PortfolioResult,
    aggregate_trades,
    simulate_fills,
)
from mrmkt.backtest.signals import (
    BacktestParams,
    entry_signals,
    exit_signals,
    vov_percentile,
)

DEFAULT_WARMUP_BARS = 300


@dataclass
class SignalSet:
    entries: pd.DataFrame
    exits: pd.DataFrame


class Strategy(ABC):
    """Signal definition: parameters, booleans per bar, description."""

    @abstractmethod
    def generate(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
    ) -> SignalSet:
        """Entry/exit booleans over full-history frames (warm-up kept)."""

    @abstractmethod
    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""


class StrategyRunner:
    """Executes any Strategy over full-history frames."""

    def __init__(
        self,
        size_pct: float = 2.0,
        fees: float = 0.001,
        stop: float = 0.08,
        max_positions: int = 50,
        warmup_bars: int = DEFAULT_WARMUP_BARS,
    ):
        self.size_pct = size_pct
        self.fees = fees
        self.stop = stop
        self.max_positions = max_positions
        self.warmup_bars = warmup_bars

    def run(
        self,
        strategy: Strategy,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        start=None,
    ) -> PortfolioResult:
        """Run a strategy; trades start at ``start`` or once
        ``warmup_bars`` of union history exist."""
        return self.run_chunked(strategy, [(close, high, low)], start=start)

    def run_chunked(
        self,
        strategy: Strategy,
        chunks: list,
        start=None,
    ) -> PortfolioResult:
        """Run a strategy over symbol chunks for bounded memory.

        ``chunks`` holds full-history ``(close, high, low)`` frames.
        Frames are downcast to float32, simulated per chunk, then the
        trade records are aggregated once over the concatenated closes."""
        all_records = []
        all_closes = []
        for close, high, low in chunks:
            if close.shape[1] == 0:
                continue
            close = close.astype(np.float32, copy=False)
            high = high.astype(np.float32, copy=False)
            low = low.astype(np.float32, copy=False)
            signals = strategy.generate(close, high, low)
            all_records.append(
                simulate_fills(
                    close,
                    signals.entries,
                    signals.exits,
                    size_pct=self.size_pct,
                    fees=self.fees,
                    stop=self.stop,
                )
            )
            all_closes.append(close)
        if not all_closes:
            raise ValueError("no symbols with price history to backtest")
        full: pd.DataFrame = pd.concat(all_closes, axis=1)
        records: pd.DataFrame = pd.concat(all_records, ignore_index=True)
        first = pd.Timestamp(start) if start is not None else full.index[self.warmup_bars]
        window = full.index >= first
        mask: pd.Series = records["Entry Timestamp"] >= first
        kept: pd.DataFrame = records.loc[mask]
        return aggregate_trades(full.loc[window], kept, self.max_positions)


class BuyRedStrategy(Strategy):
    """Long-only buy-red-in-uptrends with optional VoV compression."""

    def __init__(self, params: BacktestParams | None = None):
        self.params = params or BacktestParams()

    @classmethod
    def trend_only(cls, **overrides) -> "BuyRedStrategy":
        """Variant A: trend + range touch, no VoV filter."""
        params = BacktestParams(use_vov=False)
        for key, value in overrides.items():
            setattr(params, key, value)
        return cls(params=params)

    @classmethod
    def with_compression(cls, **overrides) -> "BuyRedStrategy":
        """Variant B: trend + range touch with VoV compression."""
        params = BacktestParams(use_vov=True)
        for key, value in overrides.items():
            setattr(params, key, value)
        return cls(params=params)

    def generate(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
    ) -> SignalSet:
        """Entry/exit booleans over full-history frames (warm-up kept)."""
        ranking = vov_percentile(close) if self.params.use_vov else None
        return SignalSet(
            entries=entry_signals(close, low, self.params, ranking),
            exits=exit_signals(close, high, self.params),
        )

    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""
        vov_rule = (
            f"VoV {self.params.vol_period}/{self.params.vol_period}/"
            f"{self.params.vov_lookback} percentile <= {self.params.vov_max:g}"
            if self.params.use_vov
            else "no VoV filter"
        )
        return (
            "Buy red in uptrends: close > "
            f"{self.params.trend_fast}D and {self.params.trend_slow}D SMA, "
            f"> {self.params.dist_lo_min:.0%} above trailing-{self.params.vov_lookback}D low, "
            f"trailing-{self.params.vov_lookback}D drawdown < {self.params.dd_max:.0%}, "
            f"daily low <= {self.params.horizon_days}D risk-range buy level; {vov_rule}."
        )


class SmaCrossStrategy(Strategy):
    """Classic golden-cross long: fast SMA crossing above slow SMA."""

    def __init__(
        self,
        fast_period: int = 50,
        slow_period: int = 200,
    ):
        if not 1 <= fast_period < slow_period:
            raise ValueError("require 1 <= fast_period < slow_period")
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
    ) -> SignalSet:
        """Enter on cross up, exit on cross down (warm-up kept)."""
        fast = pd.DataFrame(close.rolling(self.fast_period).mean())
        slow = pd.DataFrame(close.rolling(self.slow_period).mean())
        prev_fast = fast.shift(1)
        prev_slow = slow.shift(1)
        valid = close.notna() & slow.notna()
        entries = valid & (fast > slow) & (prev_fast <= prev_slow)
        exits = valid & (fast < slow) & (prev_fast >= prev_slow)
        return SignalSet(
            entries=entries.fillna(False),
            exits=exits.fillna(False),
        )

    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""
        return (
            f"Golden cross: enter when {self.fast_period}D SMA crosses above "
            f"{self.slow_period}D SMA, exit on cross down."
        )
