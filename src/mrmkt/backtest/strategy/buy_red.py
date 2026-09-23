"""Long-only buy-red-in-uptrends with optional VoV compression."""

import dataclasses
import typing

import pandas as pd

from mrmkt.backtest.signals import (
    BacktestParams,
    entry_signals,
    exit_signals,
    vov_percentile,
)
from mrmkt.backtest.strategy.base import ParamSpec, SignalSet, Strategy

BUY_RED_HELP = {
    "width": "Risk range half-width in vol-scaled units",
    "vol_period": "Trailing returns for realized volatility",
    "anchor_period": "Trailing mean the range is centered on",
    "horizon_days": "Range horizon in trading days (15 = TRADE, 63 = TREND)",
    "trend_fast": "Fast trend SMA period",
    "trend_slow": "Slow trend SMA period",
    "dist_lo_min": "Min fraction above trailing low",
    "dd_max": "Max trailing drawdown fraction",
    "vov_max": "Max vol-of-vol percentile for entries",
    "use_vov": "Require compressed vol-of-vol for entries",
    "vov_lookback": "Trailing values ranked for the percentile",
}


def _backtest_param_specs() -> dict[str, ParamSpec]:
    hints = typing.get_type_hints(BacktestParams)
    specs = {}
    for field in dataclasses.fields(BacktestParams):
        specs[field.name] = ParamSpec(
            type=hints[field.name],
            default=field.default,
            help=BUY_RED_HELP.get(field.name, ""),
        )
    return specs


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

    @classmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        """Tunable parameters with types, defaults, and help."""
        return _backtest_param_specs()

    @classmethod
    def construct(cls, kwargs: dict) -> "BuyRedStrategy":
        """Build from coerced params via BacktestParams."""
        return cls(params=BacktestParams(**kwargs))

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
