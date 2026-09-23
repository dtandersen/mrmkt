"""Vectorbt-backed trading strategies and the runner that executes them.

Strategies are pure signal definitions: parameters, ``generate()``, and
a human-readable ``describe()``. All execution lives in StrategyRunner,
which slices warm-up history and runs the vectorbt fill simulator with
an explicit portfolio overlay.
"""

from mrmkt.backtest.strategy.base import MarketContext, ParamSpec, SignalSet, Strategy
from mrmkt.backtest.strategy.buy_red import BuyRedStrategy
from mrmkt.backtest.strategy.momentum_rotation import MomentumRotationStrategy
from mrmkt.backtest.strategy.registry import (
    STRATEGIES,
    build_strategy,
    parse_params,
    register,
)
from mrmkt.backtest.strategy.runner import StrategyRunner
from mrmkt.backtest.strategy.sma_cross import SmaCrossStrategy
from mrmkt.backtest.strategy.trend_pullback import TrendPullbackStrategy

__all__ = [
    "BuyRedStrategy",
    "MarketContext",
    "MomentumRotationStrategy",
    "ParamSpec",
    "STRATEGIES",
    "SignalSet",
    "SmaCrossStrategy",
    "Strategy",
    "StrategyRunner",
    "TrendPullbackStrategy",
    "build_strategy",
    "parse_params",
    "register",
]
