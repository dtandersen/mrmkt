"""Naive dip baseline: the dumb rules buy-red must beat (validation test 2).

Buy every 5% dip from the trailing high; sell every 5% rip off the
trailing low or after a fixed hold. No ranges, no VoV, no momentum, no
gates. Results (sp500, 2024+, 10bps, executable fills): 1796 trades /
61.4% win / expectancy +0.446% / PF 1.16 — beats buy-red-B on expectancy
(+0.256%) and ties it on PF (1.15). Buy-red keeps the portfolio crown
(CAGR +18.2% vs +3.9%) via shorter holds, but the trade-level edge of
200 lines of machinery over dip+rip+hold is nil. That is the finding;
this class exists to keep every future idea honest.
"""

import pandas as pd

from mrmkt.backtest.strategy.base import MarketContext, ParamSpec, SignalSet, Strategy
from mrmkt.backtest.strategy.registry import register


@register("naive-dip")
class NaiveDipStrategy(Strategy):
    """Buy-the-dip / sell-the-rip / time-stop baseline."""

    def __init__(
        self,
        dip_pct: float = 0.05,
        rip_pct: float = 0.05,
        trail: int = 63,
        hold_days: int = 10,
    ):
        if not 0 < dip_pct < 1:
            raise ValueError("dip_pct must be in (0, 1)")
        if not rip_pct > 0:
            raise ValueError("rip_pct must be positive")
        if trail < 2:
            raise ValueError("trail must be >= 2")
        if hold_days < 1:
            raise ValueError("hold_days must be >= 1")
        self.dip_pct = dip_pct
        self.rip_pct = rip_pct
        self.trail = trail
        self.hold_days = hold_days

    @classmethod
    def param_specs(cls) -> dict[str, ParamSpec]:
        """Tunable thresholds with types, defaults, and help."""
        return {
            "dip_pct": ParamSpec(float, 0.05, "Dip from trailing high"),
            "rip_pct": ParamSpec(float, 0.05, "Rip off trailing low"),
            "trail": ParamSpec(int, 63, "Trailing window"),
            "hold_days": ParamSpec(int, 10, "Max hold"),
        }

    def generate(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        context: MarketContext | None = None,
    ) -> SignalSet:
        """Enter on dip, exit on rip or time-stop (warm-up kept)."""
        peak = close.rolling(self.trail).max()
        trough = close.rolling(self.trail).min()
        entries = (close <= peak * (1 - self.dip_pct)).fillna(False)
        time_exit = entries.shift(self.hold_days).fillna(False).astype(bool)
        rip_exit = (close >= trough * (1 + self.rip_pct)).fillna(False)
        exits = (time_exit | rip_exit).fillna(False)
        return SignalSet(entries=entries, exits=exits)

    def describe(self) -> str:
        """Human-readable rule summary for notes and logs."""
        return (
            f"Naive dip: buy {self.dip_pct:.0%} off trailing-{self.trail}D "
            f"high; sell {self.rip_pct:.0%} rip or {self.hold_days}D hold."
        )
