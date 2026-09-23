"""Simple momentum-rotation comparator (plan section 4B).

Checks whether relative strength plus a broad trend gate explains
performance without pullback/risk-range machinery: on a fixed schedule,
hold the strongest eligible names; otherwise sit in cash.

Rules, all thresholds configurable:
- Momentum: past return ending ``mom_skip`` bars ago over the preceding
  ``mom_lookback - mom_skip`` bars (point-in-time), ranked
  cross-sectionally over the full universe (``needs_universe``).
- Rebalance: every ``rebalance_days`` bars, hold the top ``top_n`` names
  by momentum (optionally requiring close above a rising ``trend_sma``).
  Names leaving the top set are exited; newly entering names are bought.
  Held positions are tracked greedily and deterministically across
  rebalance dates so entries/exits stay disjoint per bar.
- Regime: when ``use_gate`` is on and the benchmark (or the
  equal-weight universe mean fallback) is below its ``market_sma``-day
  SMA, all held positions exit and no new entries trigger (cash regime).
  ``benchmark_fallback="none"`` disables gating without a benchmark.

Fills/costs remain the engine's; the execution/accounting validation
gate is still open, so no performance claims attach to these signals.
"""

import dataclasses
import typing

import numpy as np
import pandas as pd

from mrmkt.backtest.strategy.base import MarketContext, ParamSpec, SignalSet, Strategy
from mrmkt.backtest.strategy.registry import register
from mrmkt.backtest.strategy.trend_pullback import market_gate


@dataclasses.dataclass
class MomentumRotationParams:
    mom_lookback: int = 252
    mom_skip: int = 21
    top_n: int = 20
    rebalance_days: int = 21
    market_sma: int = 200
    use_gate: bool = True
    benchmark_fallback: str = "universe"  # "universe" | "none"
    require_trend: bool = False
    trend_sma: int = 200
    rising_bars: int = 20


MOMENTUM_ROTATION_HELP = {
    "mom_lookback": "Momentum formation window in bars",
    "mom_skip": "Most-recent bars excluded from momentum",
    "top_n": "Names held after each rebalance",
    "rebalance_days": "Bars between rebalances",
    "market_sma": "Benchmark SMA period for the cash regime",
    "use_gate": "Sit in cash when the benchmark is below its SMA",
    "benchmark_fallback": "Gate input without a benchmark: universe index or none",
    "require_trend": "Only hold names above their rising trend SMA",
    "trend_sma": "Stock trend SMA period",
    "rising_bars": "Bars back for the rising-SMA comparison",
}


def _param_specs() -> dict[str, ParamSpec]:
    hints = typing.get_type_hints(MomentumRotationParams)
    return {
        field.name: ParamSpec(
            type=hints[field.name],
            default=field.default,
            help=MOMENTUM_ROTATION_HELP.get(field.name, ""),
        )
        for field in dataclasses.fields(MomentumRotationParams)
    }


@register("momentum-rotation")
class MomentumRotationStrategy(Strategy):
    """Fixed-schedule rotation into the strongest eligible names."""

    needs_universe = True

    def __init__(self, **kwargs):
        params = MomentumRotationParams(**kwargs)
        if not 0 <= params.mom_skip < params.mom_lookback:
            raise ValueError(
                f"require 0 <= mom_skip < mom_lookback, got {params.mom_skip=} "
                f"{params.mom_lookback=}"
            )
        if params.top_n < 1:
            raise ValueError(f"top_n must be at least 1, got {params.top_n!r}")
        if params.rebalance_days < 1:
            raise ValueError(
                f"rebalance_days must be at least 1, got {params.rebalance_days!r}"
            )
        if params.benchmark_fallback not in ("universe", "none"):
            raise ValueError(
                f"benchmark_fallback must be 'universe' or 'none', "
                f"got {params.benchmark_fallback!r}"
            )
        self.params = params

    @classmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        """Tunable hypothesis thresholds with types, defaults, and help."""
        return _param_specs()

    @classmethod
    def construct(cls, kwargs: dict) -> "MomentumRotationStrategy":
        """Build from coerced params via MomentumRotationParams."""
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
        del high, low
        if p.use_gate:
            gate = market_gate(
                close.index, close, context, p.market_sma, False,
                p.rising_bars, p.benchmark_fallback,
            )
        else:
            gate = pd.Series(True, index=close.index)
        past = close.shift(p.mom_skip)
        momentum = past / past.shift(p.mom_lookback - p.mom_skip) - 1
        if p.require_trend:
            trend: pd.DataFrame = pd.DataFrame(close.rolling(p.trend_sma).mean())
            tradable = (
                close.notna()
                & trend.notna()
                & (close > trend)
                & (trend > pd.DataFrame(trend.shift(p.rising_bars))).fillna(False)
            )
        else:
            tradable = close.notna() & momentum.notna()
        entries = pd.DataFrame(False, index=close.index, columns=close.columns)
        exits = pd.DataFrame(False, index=close.index, columns=close.columns)
        held: set = set()
        mom_values = momentum.to_numpy()
        gate_values = gate.to_numpy()
        tradable_values = tradable.to_numpy()
        cols = list(close.columns)
        seed_pos = -1
        if context is not None and context.test_start is not None:
            probe = pd.DatetimeIndex([context.test_start])
            found = close.index.get_indexer(probe, method="bfill").tolist()
            # Single-element probe, so at most one position; -1 means
            # test_start lies past the final bar and no seeding applies.
            for position in found:
                seed_pos = position
        schedule = set(range(0, len(close.index), p.rebalance_days))
        if 0 <= seed_pos < len(close.index):
            # Window inception is an implicit rebalance: a live portfolio
            # starting at test_start would buy its targets that day.
            schedule.add(seed_pos)
        for pos in sorted(schedule):
            if pos == seed_pos:
                # Warm-up holdings never entered the test portfolio, so
                # re-establish the full wanted set instead of diffing.
                held = set()
            if not gate_values[pos]:
                for sym in sorted(held):
                    exits.iloc[pos, cols.index(sym)] = True
                held = set()
                continue
            ranked = sorted(
                (mom_values[pos, i], cols[i])
                for i in range(len(cols))
                if tradable_values[pos, i] and not np.isnan(mom_values[pos, i])
            )
            wanted = {sym for _, sym in ranked[-p.top_n :]} if ranked else set()
            for sym in sorted(wanted - held):
                entries.iloc[pos, cols.index(sym)] = True
            for sym in sorted(held - wanted):
                exits.iloc[pos, cols.index(sym)] = True
            held = wanted
        if 0 <= seed_pos < len(close.index):
            # The test portfolio is born at test_start: positions opened
            # during warm-up never existed there, so only entries at or
            # after the seed bar may open them. (Pre-seed exits are
            # harmless no-ops in fill simulation.)
            entries.iloc[:seed_pos, :] = False
        return SignalSet(entries=entries, exits=exits)

    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""
        p = self.params
        gate = (
            f"cash when market < {p.market_sma}D SMA"
            if p.use_gate
            else "always invested (no market gate)"
        )
        trend = (
            f", requiring close above rising {p.trend_sma}D SMA"
            if p.require_trend
            else ""
        )
        return (
            f"Momentum rotation: hold top {p.top_n} by {p.mom_lookback}D "
            f"momentum skipping {p.mom_skip}D, rebalanced every "
            f"{p.rebalance_days}D; {gate}{trend}."
        )
