"""Vectorbt-backed trading strategies and the runner that executes them.

Strategies are pure signal definitions: parameters, ``generate()``, and
a human-readable ``describe()``. All execution lives in StrategyRunner,
which slices warm-up history and runs the vectorbt fill simulator with
an explicit portfolio overlay.
"""

import dataclasses
import typing
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


@dataclass
class ParamSpec:
    """One tunable strategy parameter: type, default, help."""

    type: type
    default: object
    help: str = ""


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

    @classmethod
    @abstractmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        """Tunable parameters with types, defaults, and help."""

    @classmethod
    def construct(cls, kwargs: dict) -> "Strategy":
        """Build from coerced params; override when construction differs."""
        return cls(**kwargs)


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

    @classmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        """Tunable parameters with types, defaults, and help."""
        return {
            "fast_period": ParamSpec(int, 50, "Fast SMA period"),
            "slow_period": ParamSpec(int, 200, "Slow SMA period"),
        }

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


STRATEGIES: dict[str, type[Strategy]] = {
    "buy-red": BuyRedStrategy,
    "sma-cross": SmaCrossStrategy,
}


def parse_params(text: str | None) -> dict[str, str]:
    """Parse ``k=v,k2=v2`` into raw strings; blank means defaults."""
    if not text or not text.strip():
        return {}
    parsed = {}
    for chunk in text.split(","):
        if "=" not in chunk:
            raise ValueError(f"params must look like k=v,k2=v2, got {chunk.strip()!r}")
        key, _, value = chunk.partition("=")
        key, value = key.strip(), value.strip()
        if not key or not value:
            raise ValueError(f"params must look like k=v,k2=v2, got {chunk.strip()!r}")
        parsed[key] = value
    return parsed


def build_strategy(name: str, raw: dict[str, str]) -> Strategy:
    """Build a registered strategy, coercing raw ``k=v`` strings."""
    key = name.strip().lower()
    if key not in STRATEGIES:
        raise ValueError(f"unknown strategy {name!r} (choose from {sorted(STRATEGIES)})")
    cls = STRATEGIES[key]
    specs = cls.param_specs()
    unknown = sorted(k for k in raw if k not in specs)
    if unknown:
        raise ValueError(f"unknown params {unknown} for {name} (choose from {sorted(specs)})")
    return cls.construct({k: _coerce(specs[k].type, v, k) for k, v in raw.items()})


def _coerce(pytype: type, text: str, name: str):
    stripped = text.strip()
    if pytype is bool:
        if stripped.lower() in ("1", "true", "yes", "y", "on"):
            return True
        if stripped.lower() in ("0", "false", "no", "n", "off"):
            return False
        raise ValueError(f"param {name} must be true/false, got {text!r}")
    try:
        return pytype(stripped)
    except ValueError:
        raise ValueError(f"param {name} must be {pytype.__name__}, got {text!r}") from None
