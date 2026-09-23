"""Trend + relative-strength pullback candidate (plan section 4A).

Hypothesis (not a tuned system): pullbacks are more attractive in stocks
already leading a bullish market, and a recovery trigger avoids buying a
dip that is still accelerating downward.

Rules, all thresholds configurable:
- Market gate: benchmark (e.g. SPY) close above its ``market_sma``-day
  SMA, optionally requiring the SMA to be rising. Without a benchmark in
  context, falls back to the equal-weight universe mean (explicit, not
  silent): pass ``benchmark_fallback="none"`` to disable gating.
- Stock eligibility: close above its rising ``trend_sma``-day SMA and in
  the top ``momentum_top_share`` of cross-sectional 6-12 month momentum
  excluding the most recent month. Ranks are computed over the full
  universe passed to ``generate`` (``needs_universe``), never per chunk.
- Entry: close pulled back toward its ``pullback_period``-day average
  (within ``pullback_tol``), plus a recovery trigger (close back above
  the prior day's high) unless ``recovery_bars=0``.
- Exit: ``exit_mode="trend"`` exits on a close below the trend SMA;
  ``exit_mode="range"`` additionally exits at a volatility-implied range
  top (hypothesis defaults mirroring the buy-red band shape).

All levels use information available at or before the signal bar. Fill
timing/costs remain the engine's (same close fills as every strategy);
the execution/accounting validation gate is still open, so no
performance claims attach to these signals.
"""

import dataclasses
import typing

import numpy as np
import pandas as pd

from mrmkt.backtest.strategy.base import MarketContext, ParamSpec, SignalSet, Strategy
from mrmkt.backtest.strategy.registry import register


@dataclasses.dataclass
class TrendPullbackParams:
    market_sma: int = 200
    require_rising: bool = False
    rising_bars: int = 20
    benchmark_fallback: str = "universe"  # "universe" | "none"
    trend_sma: int = 200
    mom_lookback: int = 252
    mom_skip: int = 21
    momentum_top_share: float = 0.333
    pullback_period: int = 20
    pullback_tol: float = 0.0
    recovery_bars: int = 1  # 1 = close above prior high; 0 = no recovery trigger
    exit_mode: str = "trend"  # "trend" | "range"
    width: float = 0.5
    vol_period: int = 21
    anchor_period: int = 5
    horizon_days: int = 15


TREND_PULLBACK_HELP = {
    "market_sma": "Benchmark SMA period for the market gate",
    "require_rising": "Also require the market SMA to be rising",
    "rising_bars": "Bars back for the rising-SMA comparison",
    "benchmark_fallback": "Gate input without a benchmark: universe index or none",
    "trend_sma": "Stock trend SMA period (must be rising)",
    "mom_lookback": "Momentum formation window in bars",
    "mom_skip": "Most-recent bars excluded from momentum",
    "momentum_top_share": "Top cross-sectional momentum share eligible (0-1)",
    "pullback_period": "Short average the pullback is measured against",
    "pullback_tol": "Max fraction above the short average still a pullback",
    "recovery_bars": "1 = require close above prior high; 0 = pullback touch only",
    "exit_mode": "trend = SMA break only; range = also exit at range top",
    "width": "Range exit half-width in vol-scaled units",
    "vol_period": "Trailing returns for realized volatility (range exit)",
    "anchor_period": "Trailing mean the range exit is centered on",
    "horizon_days": "Range exit horizon in trading days",
}


def _param_specs() -> dict[str, ParamSpec]:
    hints = typing.get_type_hints(TrendPullbackParams)
    return {
        field.name: ParamSpec(
            type=hints[field.name],
            default=field.default,
            help=TREND_PULLBACK_HELP.get(field.name, ""),
        )
        for field in dataclasses.fields(TrendPullbackParams)
    }


def equal_weight_index(close: pd.DataFrame) -> pd.Series:
    """Scale-invariant equal-weight market level from ``close``.

    Cumulated mean of per-bar simple returns, so multiplying any
    ticker's price series by a constant leaves the index unchanged
    (unlike an arithmetic mean of nominal prices, which moves with
    arbitrary price scales). Bars with no coverage contribute a zero
    return."""
    returns: pd.Series = close.pct_change().replace(
        [np.inf, -np.inf], np.nan
    ).mean(axis=1, skipna=True).fillna(0.0)
    level: pd.Series = pd.Series((1 + returns).cumprod(), index=close.index)
    return level


def market_gate(
    index: pd.Index,
    close: pd.DataFrame,
    context: MarketContext | None,
    market_sma: int,
    require_rising: bool,
    rising_bars: int,
    fallback: str,
) -> pd.Series:
    """Per-bar market-gate booleans aligned to ``index``.

    Uses the context benchmark when present; otherwise a
    scale-invariant equal-weight return index over the universe
    (``fallback="universe"``) or no gating at all
    (``fallback="none"``). Only past values feed each bar.
    """
    if context is not None and context.benchmark is not None:
        market = context.benchmark.reindex(index).ffill()
    elif fallback == "none":
        return pd.Series(True, index=index)
    elif fallback == "universe":
        market = equal_weight_index(close)
    else:
        raise ValueError(f"benchmark_fallback must be 'universe' or 'none', got {fallback!r}")
    sma: pd.Series = pd.Series(market.rolling(market_sma).mean())
    gate = market > sma
    if require_rising:
        gate &= sma > sma.shift(rising_bars)
    return gate.fillna(False)


def momentum_rank(close: pd.DataFrame, lookback: int, skip: int) -> pd.DataFrame:
    """Cross-sectional percentile rank (0-1) of past momentum per bar.

    Momentum at bar ``t`` is the return ending ``skip`` bars ago over the
    preceding ``lookback - skip`` bars: strictly past-only.
    """
    if not 0 <= skip < lookback:
        raise ValueError(f"require 0 <= mom_skip < mom_lookback, got skip={skip} lookback={lookback}")
    past = close.shift(skip)
    momentum = past / past.shift(lookback - skip) - 1
    return momentum.rank(axis=1, pct=True)


@register("trend-pullback")
class TrendPullbackStrategy(Strategy):
    """Pullback entries in leading stocks under a market gate."""

    needs_universe = True

    def __init__(self, **kwargs):
        params = TrendPullbackParams(**kwargs)
        if params.exit_mode not in ("trend", "range"):
            raise ValueError(f"exit_mode must be 'trend' or 'range', got {params.exit_mode!r}")
        if params.benchmark_fallback not in ("universe", "none"):
            raise ValueError(
                f"benchmark_fallback must be 'universe' or 'none', "
                f"got {params.benchmark_fallback!r}"
            )
        if not 0 < params.momentum_top_share <= 1:
            raise ValueError(
                f"momentum_top_share must be in (0, 1], got {params.momentum_top_share!r}"
            )
        if params.recovery_bars not in (0, 1):
            raise ValueError(
                f"recovery_bars must be 0 or 1, got {params.recovery_bars!r}"
            )
        self.params = params

    @classmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        """Tunable hypothesis thresholds with types, defaults, and help."""
        return _param_specs()

    @classmethod
    def construct(cls, kwargs: dict) -> "TrendPullbackStrategy":
        """Build from coerced params via TrendPullbackParams."""
        return cls(**kwargs)

    def generate(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        context: MarketContext | None = None,
    ) -> SignalSet:
        """Entry/exit booleans over full-history frames (warm-up kept)."""
        p = self.params
        gate = market_gate(
            close.index, close, context, p.market_sma, p.require_rising,
            p.rising_bars, p.benchmark_fallback,
        )
        trend: pd.DataFrame = pd.DataFrame(close.rolling(p.trend_sma).mean())
        rising = trend > pd.DataFrame(trend.shift(p.rising_bars))
        rank = momentum_rank(close, p.mom_lookback, p.mom_skip)
        eligible = (
            close.notna()
            & trend.notna()
            & (close > trend)
            & rising.fillna(False)
            & (rank >= 1 - p.momentum_top_share)
        )
        short_avg: pd.DataFrame = pd.DataFrame(close.rolling(p.pullback_period).mean())
        pulled_back = close.notna() & short_avg.notna() & (
            close <= short_avg * (1 + p.pullback_tol)
        )
        if p.recovery_bars:
            recovered = close > high.shift(1)
        else:
            recovered = pd.DataFrame(True, index=close.index, columns=close.columns)
        entries = (
            eligible & pulled_back & recovered & gate.to_numpy()[:, None]
        ).fillna(False)

        if p.exit_mode == "range":
            anchor: pd.DataFrame = pd.DataFrame(close.rolling(p.anchor_period).mean())
            dvol: pd.DataFrame = np.log(close / close.shift(1)).rolling(p.vol_period).std(ddof=1)
            sell = anchor * (1 + p.width * dvol * np.sqrt(p.horizon_days))
            at_top = high.notna() & sell.notna() & (high >= sell)
        else:
            at_top = pd.DataFrame(False, index=close.index, columns=close.columns)
        broke_trend = close.notna() & trend.notna() & (close < trend)
        exits = (at_top | broke_trend).fillna(False)
        return SignalSet(entries=entries, exits=exits)

    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""
        p = self.params
        gate = f"market > {p.market_sma}D SMA" + (
            f" and rising ({p.rising_bars}D)" if p.require_rising else ""
        )
        recovery = "close above prior high" if p.recovery_bars else "pullback touch only"
        return (
            f"Trend pullback: {gate}; close above rising {p.trend_sma}D SMA, "
            f"top {p.momentum_top_share:.0%} momentum ({p.mom_lookback}D "
            f"skip {p.mom_skip}D); enter on pullback to {p.pullback_period}D "
            f"avg + {recovery}; exit {p.exit_mode}."
        )
