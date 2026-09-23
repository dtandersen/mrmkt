"""Strategy contract and shared signal/result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


@dataclass
class MarketContext:
    """Extra non-tradable inputs for signal generation.

    ``benchmark`` is a full-history close series for the market gate
    (e.g. SPY). It is never added to the tradable universe: strategies
    must only read it for gating, and the runner never includes it in
    fill simulation or portfolio aggregation.
    """

    benchmark: pd.Series | None = None
    """Optional non-tradable market close series for regime gating."""

    test_start: pd.Timestamp | None = None
    """First bar of the test window.

    Stateful strategies (e.g. rotation) use this to (re)establish
    positions exactly at window inception, since the runner drops
    records entered before this bar. Stateless per-bar strategies
    ignore it."""


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

    #: Set True when signals need the full symbol universe (e.g.
    #: cross-sectional ranks). The runner then concatenates chunks for
    #: one universe-wide ``generate`` call while still chunking the
    #: fill simulation for bounded memory.
    needs_universe: bool = False

    @abstractmethod
    def generate(
        self,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        context: MarketContext | None = None,
    ) -> SignalSet:
        """Entry/exit booleans over full-history frames (warm-up kept).

        ``context`` carries non-tradable inputs such as the market
        benchmark; strategies that do not need it ignore it."""

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
