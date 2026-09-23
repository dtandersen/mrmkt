"""Classic golden-cross long: fast SMA crossing above slow SMA."""

import pandas as pd

from mrmkt.backtest.strategy.base import ParamSpec, SignalSet, Strategy


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
