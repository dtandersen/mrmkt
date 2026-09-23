"""Strategy contract and shared signal/result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pandas as pd


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
