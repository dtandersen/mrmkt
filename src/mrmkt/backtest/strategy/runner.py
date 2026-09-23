"""Executes any Strategy over full-history frames."""

from typing import cast

import numpy as np
import pandas as pd

from mrmkt.backtest.portfolio import PortfolioResult, aggregate_trades, simulate_fills
from mrmkt.backtest.strategy.base import MarketContext, Strategy

DEFAULT_WARMUP_BARS = 300


class StrategyRunner:
    """Executes any Strategy over full-history frames."""

    def __init__(
        self,
        size_pct: float = 2.0,
        fees: float = 0.0,
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
        benchmark: pd.Series | None = None,
    ) -> PortfolioResult:
        """Run a strategy; trades start at ``start`` or once
        ``warmup_bars`` of union history exist.

        ``benchmark`` is an optional non-tradable market series (e.g.
        SPY closes) forwarded as signal context for gating."""
        return self.run_chunked(strategy, [(close, high, low)], start=start, benchmark=benchmark)

    def run_chunked(
        self,
        strategy: Strategy,
        chunks: list,
        start=None,
        benchmark: pd.Series | None = None,
    ) -> PortfolioResult:
        """Run a strategy over symbol chunks for bounded memory.

        ``chunks`` holds full-history ``(close, high, low)`` frames.
        Frames are downcast to float32, simulated per chunk, then the
        trade records are aggregated once over the concatenated closes.
        ``benchmark`` is forwarded as non-tradable signal context and
        never enters fill simulation. Strategies with
        ``needs_universe`` get one universe-wide ``generate`` call
        (correct cross-sectional ranks) while fills stay chunked. The
        test-window start is shared via context so stateful strategies
        can (re)establish positions at window inception."""
        prepared = []
        for close, high, low in chunks:
            if close.shape[1] == 0:
                continue
            prepared.append(
                (
                    close.astype(np.float32, copy=False),
                    high.astype(np.float32, copy=False),
                    low.astype(np.float32, copy=False),
                )
            )
        if not prepared:
            raise ValueError("no symbols with price history to backtest")
        union_idx = prepared[0][0].index
        for close, _, _ in prepared[1:]:
            union_idx = union_idx.union(close.index)
        if start is not None:
            first_ts = cast(pd.Timestamp, pd.Timestamp(start))
        else:
            bar = union_idx[self.warmup_bars]
            if pd.isna(bar):
                raise ValueError("test window start bar is not a valid timestamp")
            # DatetimeIndex bars are Timestamps at runtime; the stubs keep
            # NaTType in the union, which the isna guard above excludes.
            first_ts = cast(pd.Timestamp, bar)
        context = MarketContext(benchmark=benchmark, test_start=first_ts)
        if getattr(strategy, "needs_universe", False):
            full_close = pd.concat([c for c, _, _ in prepared], axis=1)
            full_high = pd.concat([h for _, h, _ in prepared], axis=1)
            full_low = pd.concat([lo for _, _, lo in prepared], axis=1)
            signals = strategy.generate(full_close, full_high, full_low, context=context)
            all_records = []
            for close, high, low in prepared:
                cols = list(close.columns)
                all_records.append(
                    simulate_fills(
                        close,
                        pd.DataFrame(signals.entries[cols]),
                        pd.DataFrame(signals.exits[cols]),
                        size_pct=self.size_pct,
                        fees=self.fees,
                        stop=self.stop,
                        high=high,
                        low=low,
                    )
                )
            all_closes = [c for c, _, _ in prepared]
        else:
            all_records = []
            all_closes = []
            for close, high, low in prepared:
                signals = strategy.generate(close, high, low, context=context)
                all_records.append(
                    simulate_fills(
                        close,
                        signals.entries,
                        signals.exits,
                        size_pct=self.size_pct,
                        fees=self.fees,
                        stop=self.stop,
                        high=high,
                        low=low,
                    )
                )
                all_closes.append(close)
        full: pd.DataFrame = pd.concat(all_closes, axis=1)
        records: pd.DataFrame = pd.concat(all_records, ignore_index=True)
        first = first_ts
        window = full.index >= first
        mask: pd.Series = records["Entry Timestamp"] >= first
        kept: pd.DataFrame = records.loc[mask]
        return aggregate_trades(full.loc[window], kept, self.max_positions, self.fees)
