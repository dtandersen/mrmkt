"""Executes any Strategy over full-history frames."""

import numpy as np
import pandas as pd

from mrmkt.backtest.portfolio import PortfolioResult, aggregate_trades, simulate_fills
from mrmkt.backtest.strategy.base import Strategy

DEFAULT_WARMUP_BARS = 300


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
