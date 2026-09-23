"""VectorBT-backed backtesting engine for mrmkt.

Strategy (v1.1): long-only "buy red in uptrends". Entries fire when a
symbol is above its TREND/TAIL SMAs, passes drawdown vetoes, and its
daily low touches the TRADE low end of the risk range; variant B also
requires compressed vol-of-vol. Exits use the contemporaneous range
top (ranges update every bar, per Hedgeye's dynamic signals), TREND
breaks, and a stop-loss.
"""

from mrmkt.backtest.portfolio import PortfolioResult, run_portfolio
from mrmkt.backtest.signals import BacktestParams, entry_signals, exit_signals

__all__ = [
    "BacktestParams",
    "PortfolioResult",
    "entry_signals",
    "exit_signals",
    "run_portfolio",
]
