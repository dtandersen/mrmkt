"""Executes any Strategy over full-history frames."""

from typing import cast

import numpy as np
import pandas as pd

from mrmkt.backtest.portfolio import (
    PortfolioResult,
    aggregate_trades,
    simulate_fills,
    simulate_limit_touch_fills,
)
from mrmkt.backtest.strategy.base import MarketContext, SignalSet, Strategy

DEFAULT_WARMUP_BARS = 300


def _apply_fill_lag(signals: SignalSet, fill_lag: int) -> SignalSet:
    """Delay fills so signals are executable: known at bar close, filled later.

    ``fill_lag=0`` fills at the signal bar close (requires acting on the
    touch before the close prints — optimistic). ``fill_lag=1`` fills at
    the next bar close (clearly executable, mildly conservative)."""
    if fill_lag == 0:
        return signals
    return SignalSet(
        entries=signals.entries.shift(fill_lag).fillna(False).astype(bool),
        exits=signals.exits.shift(fill_lag).fillna(False).astype(bool),
    )


def _limit_fill_prices(
    entries: pd.DataFrame, limits: pd.DataFrame, fill_lag: int
) -> dict:
    """Map ``(symbol, fill_timestamp)`` to the resting limit for kept entries.

    Only entries with a finite limit get an override (NaN limits are market
    fills priced at the close); the touch gate in :func:`_apply_limit_touch`
    decides which entries are kept. Filling at the limit is exact when the
    fill bar touches then closes at/above it, and conservative on
    gap-throughs (a real order improves toward the open, but opens are not
    in the HLC pipeline, so that improvement is deliberately unmodeled)."""
    ref = limits.shift(fill_lag)
    kept = entries.fillna(False).to_numpy() & ref.notna().to_numpy()
    out: dict = {}
    for j, col in enumerate(entries.columns):
        for i in entries.index[kept[:, j]]:
            px = ref.loc[i, col]
            try:
                price = float(px)
            except (TypeError, ValueError):
                continue
            if np.isfinite(price):
                out[(str(col), i)] = price
    return out


def _apply_limit_touch(
    entries: pd.DataFrame, limits: pd.DataFrame, low: pd.DataFrame, fill_lag: int
) -> pd.DataFrame:
    """Keep only entries whose resting limit is touched on the fill bar.

    The limit is known at the signal-bar close; the fill bar is
    ``fill_lag`` bars later. An entry fills only if that bar's low
    reaches the limit (a one-session resting order). NaN limits mean a
    market entry and are never gated. This gate decides *which* entries
    fill; *pricing* is set by ``fill_price`` (fill-bar close by default,
    resting limit with ``fill_price='limit'``). Under close pricing the
    fill cuts both ways versus a real resting fill at the limit:
    at-or-above the limit it overstates cost (conservative), below the
    limit — a bar that touched then closed under it — it understates cost
    (optimistic). Same-day risk after an intraday touch is not modeled:
    the position is treated as opened at the close, so an intrabar
    round trip through the stop on the fill bar itself is invisible here.
    The realism gain over the close model is the miss: untouched limits
    simply do not fill."""
    ref = limits.shift(fill_lag)
    touched = (low <= ref).fillna(False)
    market = ref.isna()
    return (entries & (market | touched)).fillna(False).astype(bool)


class StrategyRunner:
    """Executes any Strategy over full-history frames."""

    def __init__(
        self,
        size_pct: float = 2.0,
        fees: float = 0.0,
        stop: float = 0.08,
        max_positions: int = 50,
        warmup_bars: int = DEFAULT_WARMUP_BARS,
        fill_lag: int = 1,
        fill_model: str = "close",
        fill_price: str = "close",
    ):
        if fill_lag not in (0, 1):
            raise ValueError("fill_lag must be 0 (signal close) or 1 (next close)")
        if fill_model not in ("close", "limit-touch"):
            raise ValueError(
                "fill_model must be 'close' (fill every signal) or "
                "'limit-touch' (fill only touched resting limits)"
            )
        if fill_price not in ("close", "limit"):
            raise ValueError(
                "fill_price must be 'close' (fill-bar close) or "
                "'limit' (resting limit price)"
            )
        if fill_price != "close" and fill_model != "limit-touch":
            raise ValueError("fill_price='limit' needs fill_model='limit-touch'")
        if not 0 < size_pct <= 100:
            raise ValueError("size_pct must be between 0 and 100")
        if not 0 < stop < 1:
            raise ValueError("stop must be between 0 and 1")
        if fees < 0:
            raise ValueError("fees must be >= 0")
        self.size_pct = size_pct
        self.fees = fees
        self.stop = stop
        self.max_positions = max_positions
        self.warmup_bars = warmup_bars
        self.fill_lag = fill_lag
        self.fill_model = fill_model
        self.fill_price = fill_price

    def _limits_or_raise(
        self,
        strategy: Strategy,
        close: pd.DataFrame,
        high: pd.DataFrame,
        low: pd.DataFrame,
        context: MarketContext,
    ) -> pd.DataFrame | None:
        """Limit frame for touch gating, or None under the close model."""
        if self.fill_model != "limit-touch":
            return None
        limits = strategy.entry_limits(close, high, low, context)
        if limits is None:
            raise ValueError(
                f"strategy {type(strategy).__name__} does not provide entry "
                "limits for fill_model='limit-touch'"
            )
        return limits

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
        return self.run_chunked(
            strategy, [(close, high, low)], start=start, benchmark=benchmark
        )

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
        entry_prices: dict = {}
        if getattr(strategy, "needs_universe", False):
            full_close = pd.concat([c for c, _, _ in prepared], axis=1)
            full_high = pd.concat([h for _, h, _ in prepared], axis=1)
            full_low = pd.concat([lo for _, _, lo in prepared], axis=1)
            signals = _apply_fill_lag(
                strategy.generate(full_close, full_high, full_low, context=context),
                self.fill_lag,
            )
            limits = self._limits_or_raise(
                strategy, full_close, full_high, full_low, context
            )
            all_records = []
            for close, high, low in prepared:
                cols = list(close.columns)
                entries = pd.DataFrame(signals.entries[cols])
                exits = pd.DataFrame(signals.exits[cols])
                if limits is not None:
                    chunk_limits = pd.DataFrame(limits[cols])
                    entries = _apply_limit_touch(
                        entries, chunk_limits, low, self.fill_lag
                    )
                    if self.fill_price == "limit":
                        entry_prices.update(
                            _limit_fill_prices(entries, chunk_limits, self.fill_lag)
                        )
                        all_records.append(
                            simulate_limit_touch_fills(
                                close,
                                high,
                                low,
                                entries,
                                exits,
                                chunk_limits,
                                self.fill_lag,
                                self.stop,
                            )
                        )
                        continue
                all_records.append(
                    simulate_fills(
                        close,
                        entries,
                        exits,
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
                signals = _apply_fill_lag(
                    strategy.generate(close, high, low, context=context), self.fill_lag
                )
                entries = signals.entries
                limits = self._limits_or_raise(strategy, close, high, low, context)
                if limits is not None:
                    entries = _apply_limit_touch(entries, limits, low, self.fill_lag)
                    if self.fill_price == "limit":
                        entry_prices.update(
                            _limit_fill_prices(entries, limits, self.fill_lag)
                        )
                        all_records.append(
                            simulate_limit_touch_fills(
                                close,
                                high,
                                low,
                                entries,
                                signals.exits,
                                limits,
                                self.fill_lag,
                                self.stop,
                            )
                        )
                        all_closes.append(close)
                        continue
                all_records.append(
                    simulate_fills(
                        close,
                        entries,
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
        return aggregate_trades(
            full.loc[window],
            kept,
            self.max_positions,
            self.fees,
            entry_prices or None,
        )
