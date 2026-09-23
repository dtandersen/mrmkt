"""Vectorbt-backed trading strategies as single classes.

Each strategy bundles its configuration, signal generation, warm-up
slicing, and execution so variants are instantiable and comparable and
the CLI stays thin. Engines underneath: pure signal builders plus the
vectorbt fill simulator with an explicit portfolio overlay.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd

from mrmkt.backtest.portfolio import PortfolioResult, run_portfolio
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
    vov: pd.DataFrame | None


class VectorStrategy(ABC):
    """Shared warm-up slicing and execution for signal strategies."""

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

    def backtest(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        start=None,
    ) -> PortfolioResult:
        """Run over full-history frames; trades start at ``start`` or once
        ``warmup_bars`` of union history exist."""
        signals = self.generate(close, high, low)
        first = (
            pd.Timestamp(start)
            if start is not None
            else close.index[self.warmup_bars]
        )
        window = close.index >= first
        return run_portfolio(
            close.loc[window],
            signals.entries.loc[window],
            signals.exits.loc[window],
            size_pct=self.size_pct,
            fees=self.fees,
            stop=self.stop,
            max_positions=self.max_positions,
        )


class BuyRedStrategy(VectorStrategy):
    """Long-only buy-red-in-uptrends with optional VoV compression."""

    def __init__(
        self,
        params: BacktestParams | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
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
            vov=ranking,
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
            f"daily low <= {self.params.horizon_days}D risk-range buy level; {vov_rule}. "
            f"Exit range top / TREND break / {self.stop:.0%} stop. "
            f"{self.size_pct:g}% sizing, {self.fees:.1%} fees, cap {self.max_positions}."
        )


class SmaCrossStrategy(VectorStrategy):
    """Classic golden-cross long: fast SMA crossing above slow SMA."""

    def __init__(
        self,
        fast_period: int = 50,
        slow_period: int = 200,
        **kwargs,
    ):
        super().__init__(**kwargs)
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
            vov=None,
        )

    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""
        return (
            f"Golden cross: enter when {self.fast_period}D SMA crosses above "
            f"{self.slow_period}D SMA, exit on cross down. "
            f"Exit also on {self.stop:.0%} stop. "
            f"{self.size_pct:g}% sizing, {self.fees:.1%} fees, cap {self.max_positions}."
        )
