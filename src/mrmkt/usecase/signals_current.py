"""Current strategy-signal discovery over stored bars (no fills implied).

Signal booleans are known only after a bar closes. The output reports
the signal date and that bar's close separately from any fill notion:
no fill price is shown and none is implied. Ticker identity comes from
the scored frames; backtest trade attribution additionally carries
``TradeSummary.symbol`` from the fill records' ``Column``.
"""

from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

from mrmkt.backtest.strategy import build_strategy
from mrmkt.usecase.universe import MEMBERSHIP_VINTAGE_NOTE

FILL_CONVENTION_NOTE = (
    "signals are known after bar close; no fill price is shown or implied "
    "(execution would be a later bar or a documented limit-fill model)"
)


@dataclass
class SignalsRequest:
    include_tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)
    as_of: date | None = None
    strategy_name: str = "buy-red"
    params: dict[str, str] = field(default_factory=dict)
    benchmark_symbol: str | None = None
    include_benchmark: bool = False
    top_n: int | None = None


@dataclass
class SignalRow:
    symbol: str
    signal_date: date
    close: float
    status: str  # entry_signal | exit_signal | neutral
    last_entry_date: date | None
    last_entry_close: float | None
    last_exit_date: date | None
    last_exit_close: float | None
    days_since_entry: int | None
    days_since_exit: int | None
    n_bars: int
    dist_lo: float | None = None
    drawdown: float | None = None
    vov_pct: float | None = None
    above_fast: bool | None = None
    above_slow: bool | None = None
    mom_value: float | None = None
    mom_rank: float | None = None
    pullback_dist: float | None = None
    gate: bool | None = None


@dataclass
class SignalsResult:
    as_of: date
    data_vintage: date | None
    strategy_name: str
    params: dict[str, str]
    description: str
    benchmark_symbol: str | None
    benchmark_resolved: bool
    include_tags: list[str]
    exclude_tags: list[str]
    universe_size: int
    rows: list[SignalRow]
    request: SignalsRequest


class SignalsUseCase:
    """Score the current bar per symbol through a registered strategy."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: SignalsRequest) -> SignalsResult:
        """Run signal discovery; raises ValueError on bad strategy/params."""
        from mrmkt.usecase.universe import resolve_universe

        strategy = build_strategy(request.strategy_name, dict(request.params))
        symbols = resolve_universe(
            self.repository, request.include_tags, request.exclude_tags
        )
        if request.benchmark_symbol and not request.include_benchmark:
            # The benchmark is non-tradable gate context; drop it from the
            # scored universe unless explicitly included.
            symbols = [s for s in symbols if s != request.benchmark_symbol]
        bars_by_symbol: dict = {}
        for price in self.repository.list_prices_for_symbols(
            symbols, date.min, request.as_of if request.as_of is not None else date.max
        ):
            bars_by_symbol.setdefault(price.symbol, []).append(price)

        as_of = request.as_of
        if as_of is None:
            known = [b.date for bars in bars_by_symbol.values() for b in bars]
            as_of = max(known) if known else None
            if as_of is None:
                return SignalsResult(
                    as_of=None,  # type: ignore[arg-type]
                    data_vintage=None,
                    strategy_name=request.strategy_name,
                    params=dict(request.params),
                    description=strategy.describe(),
                    include_tags=sorted(request.include_tags),
                    exclude_tags=sorted(request.exclude_tags),
                    universe_size=0,
                    rows=[],
                    request=request,
                )

        frames: dict[str, list] = {}
        for symbol in symbols:
            bars = sorted(
                (b for b in bars_by_symbol.get(symbol, []) if b.date <= as_of),
                key=lambda b: b.date,
            )
            if bars:
                frames[symbol] = bars
        if not frames:
            benchmark, benchmark_resolved = _load_benchmark(
                self.repository, request.benchmark_symbol, as_of
            )
            return SignalsResult(
                as_of=as_of,
                data_vintage=None,
                strategy_name=request.strategy_name,
                params=dict(request.params),
                description=strategy.describe(),
                benchmark_symbol=request.benchmark_symbol,
                benchmark_resolved=benchmark_resolved,
                include_tags=sorted(request.include_tags),
                exclude_tags=sorted(request.exclude_tags),
                universe_size=len(symbols),
                rows=[],
                request=request,
            )

        index = sorted({b.date for bars in frames.values() for b in bars})
        idx = pd.DatetimeIndex(index)
        closes = pd.DataFrame(
            {
                symbol: pd.Series({b.date: b.close for b in bars}).reindex(index)
                for symbol, bars in frames.items()
            },
            index=idx,
        )
        highs = pd.DataFrame(
            {
                symbol: pd.Series({b.date: b.high for b in bars}).reindex(index)
                for symbol, bars in frames.items()
            },
            index=idx,
        )
        lows = pd.DataFrame(
            {
                symbol: pd.Series({b.date: b.low for b in bars}).reindex(index)
                for symbol, bars in frames.items()
            },
            index=idx,
        )
        from mrmkt.backtest.strategy.base import MarketContext

        benchmark, benchmark_resolved = _load_benchmark(
            self.repository, request.benchmark_symbol, as_of
        )
        context = MarketContext(benchmark=benchmark)
        signals = strategy.generate(closes, highs, lows, context=context)
        attribution = _attribution(strategy, closes, context, as_of)

        rows: list[SignalRow] = []
        for symbol, bars in frames.items():
            last_bar = bars[-1]
            entry_dates = list(signals.entries.index[signals.entries[symbol].fillna(False)])
            exit_dates = list(signals.exits.index[signals.exits[symbol].fillna(False)])
            last_entry = entry_dates[-1].date() if entry_dates else None
            last_exit = exit_dates[-1].date() if exit_dates else None
            if last_bar.date == as_of and bool(signals.entries.loc[idx[-1], symbol]):
                status = "entry_signal"
            elif last_bar.date == as_of and bool(signals.exits.loc[idx[-1], symbol]):
                status = "exit_signal"
            else:
                status = "neutral"
            attr = attribution.get(symbol, {})
            rows.append(
                SignalRow(
                    symbol=symbol,
                    signal_date=last_bar.date,
                    close=last_bar.close,
                    status=status,
                    last_entry_date=last_entry,
                    last_entry_close=(
                        closes.loc[pd.Timestamp(last_entry), symbol]
                        if last_entry is not None
                        else None
                    ),
                    last_exit_date=last_exit,
                    last_exit_close=(
                        closes.loc[pd.Timestamp(last_exit), symbol]
                        if last_exit is not None
                        else None
                    ),
                    days_since_entry=(
                        (as_of - last_entry).days if last_entry is not None else None
                    ),
                    days_since_exit=(
                        (as_of - last_exit).days if last_exit is not None else None
                    ),
                    n_bars=len(bars),
                    dist_lo=attr.get("dist_lo"),
                    drawdown=attr.get("drawdown"),
                    vov_pct=attr.get("vov_pct"),
                    above_fast=attr.get("above_fast"),
                    above_slow=attr.get("above_slow"),
                    mom_value=attr.get("mom_value"),
                    mom_rank=attr.get("mom_rank"),
                    pullback_dist=attr.get("pullback_dist"),
                    gate=attr.get("gate"),
                )
            )
        vintage = max((r.signal_date for r in rows), default=None)
        if request.top_n is not None:
            rows = rows[: request.top_n]
        return SignalsResult(
            as_of=as_of,
            data_vintage=vintage,
            strategy_name=request.strategy_name,
            params=dict(request.params),
            description=strategy.describe(),
            benchmark_symbol=request.benchmark_symbol,
            benchmark_resolved=benchmark_resolved,
            include_tags=sorted(request.include_tags),
            exclude_tags=sorted(request.exclude_tags),
            universe_size=len(symbols),
            rows=rows,
            request=request,
        )


def _load_benchmark(repository, benchmark_symbol: str | None, as_of: date):
    """Load benchmark closes up to as-of; (series|None, resolved?)."""
    if not benchmark_symbol:
        return None, False
    bars = sorted(
        (
            b
            for b in repository.list_prices(benchmark_symbol, date.min, as_of)
            if b.date <= as_of
        ),
        key=lambda b: b.date,
    )
    if not bars:
        return None, False
    return pd.Series({b.date: b.close for b in bars}).sort_index(), True


def _attribution(strategy, closes: pd.DataFrame, context, as_of: date) -> dict:
    """Per-symbol ranking inputs; BuyRed, TrendPullback, and Rotation."""
    from mrmkt.backtest.strategy.buy_red import BuyRedStrategy
    from mrmkt.backtest.strategy.momentum_rotation import MomentumRotationStrategy
    from mrmkt.backtest.strategy.trend_pullback import TrendPullbackStrategy

    if isinstance(strategy, BuyRedStrategy):
        return _buy_red_attribution(strategy, closes, as_of)
    if isinstance(strategy, TrendPullbackStrategy):
        return _trend_pullback_attribution(strategy, closes, context, as_of)
    if isinstance(strategy, MomentumRotationStrategy):
        return _rotation_attribution(strategy, closes, context, as_of)
    return {}


def _trend_pullback_attribution(strategy, closes: pd.DataFrame, context, as_of: date) -> dict:
    """Momentum value/rank, trend/rising state, pullback gap, gate."""
    from mrmkt.backtest.strategy.trend_pullback import market_gate, momentum_rank

    p = strategy.params
    stamp = pd.Timestamp(as_of)
    if stamp not in closes.index:
        return {}
    trend: pd.DataFrame = pd.DataFrame(closes.rolling(p.trend_sma).mean())
    rising = trend > pd.DataFrame(trend.shift(p.rising_bars))
    short: pd.DataFrame = pd.DataFrame(closes.rolling(p.pullback_period).mean())
    rank = momentum_rank(closes, p.mom_lookback, p.mom_skip)
    past = closes.shift(p.mom_skip)
    mom_value = past / past.shift(p.mom_lookback - p.mom_skip) - 1
    gate = market_gate(
        closes.index, closes, context, p.market_sma, p.require_rising,
        p.rising_bars, p.benchmark_fallback,
    )
    out = {}
    for symbol in closes.columns:
        close = closes.loc[stamp, symbol]
        level = trend.loc[stamp, symbol]
        avg = short.loc[stamp, symbol]
        out[symbol] = {
            "mom_value": _num(mom_value.loc[stamp, symbol]),
            "mom_rank": _num(rank.loc[stamp, symbol]),
            "above_fast": None,
            "above_slow": (
                bool(close > level) if pd.notna(close) and pd.notna(level) else None
            ),
            "pullback_dist": (
                _num((close - avg) / avg)
                if pd.notna(close) and pd.notna(avg) and avg != 0
                else None
            ),
            "gate": bool(gate.loc[stamp]) if stamp in gate.index else None,
        }
        risen = rising.loc[stamp, symbol]
        out[symbol]["above_fast"] = bool(risen) if pd.notna(risen) else None
    return out


def _rotation_attribution(strategy, closes: pd.DataFrame, context, as_of: date) -> dict:
    """Momentum value/rank and cash-regime gate for the comparator."""
    from mrmkt.backtest.strategy.trend_pullback import market_gate

    p = strategy.params
    stamp = pd.Timestamp(as_of)
    if stamp not in closes.index:
        return {}
    past = closes.shift(p.mom_skip)
    mom_value = past / past.shift(p.mom_lookback - p.mom_skip) - 1
    rank = mom_value.loc[stamp].rank(pct=True)
    if p.use_gate:
        gate = market_gate(
            closes.index, closes, context, p.market_sma, False,
            p.rising_bars, p.benchmark_fallback,
        )
        gate_at = bool(gate.loc[stamp]) if stamp in gate.index else None
    else:
        gate_at = True
    return {
        symbol: {
            "mom_value": _num(mom_value.loc[stamp, symbol]),
            "mom_rank": _num(rank.loc[stamp]),
            "gate": gate_at,
        }
        for symbol in closes.columns
    }


def _buy_red_attribution(strategy, closes: pd.DataFrame, as_of: date) -> dict:
    from mrmkt.backtest.signals import _levels, vov_percentile

    params = strategy.params
    sma_fast, sma_slow, _, _, dist_lo, drawdown, _ = _levels(closes, params)
    ranking = (
        vov_percentile(closes, vol_period=params.vol_period, lookback=params.vov_lookback)
        if params.use_vov
        else None
    )
    stamp = pd.Timestamp(as_of)
    out = {}
    for symbol in closes.columns:
        if stamp not in closes.index:
            continue
        close = closes.loc[stamp, symbol]
        fast = sma_fast.loc[stamp, symbol]
        slow = sma_slow.loc[stamp, symbol]
        out[symbol] = {
            "dist_lo": _num(dist_lo.loc[stamp, symbol]),
            "drawdown": _num(drawdown.loc[stamp, symbol]),
            "vov_pct": _num(ranking.loc[stamp, symbol]) if ranking is not None else None,
            "above_fast": bool(close > fast) if pd.notna(close) and pd.notna(fast) else None,
            "above_slow": bool(close > slow) if pd.notna(close) and pd.notna(slow) else None,
        }
    return out


def _num(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if pd.notna(result) else None


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return repr(value)
    return str(value)


SIGNALS_COLUMNS = [
    "symbol",
    "signal_date",
    "close",
    "status",
    "last_entry_date",
    "last_entry_close",
    "last_exit_date",
    "last_exit_close",
    "days_since_entry",
    "days_since_exit",
    "n_bars",
    "dist_lo",
    "drawdown",
    "vov_pct",
    "above_fast",
    "above_slow",
    "mom_value",
    "mom_rank",
    "pullback_dist",
    "gate",
]


def render_csv(result: SignalsResult) -> str:
    """Deterministic CSV: `# key=value` header, then per-symbol rows."""
    lines = [
        "# generator=mrmkt signals current",
        f"# strategy={result.strategy_name}",
        f"# params={','.join(f'{k}={v}' for k, v in sorted(result.params.items())) or '(defaults)'}",
        f"# rules={result.description}",
        f"# benchmark={result.benchmark_symbol or '(none)'} "
        f"({'resolved' if result.benchmark_resolved else 'missing; strategies use their configured fallback'})",
        f"# benchmark_tradable={'true' if result.request.include_benchmark else 'false'}",        f"# as_of={result.as_of.isoformat() if result.as_of else ''}",
        f"# data_vintage={result.data_vintage.isoformat() if result.data_vintage else ''}",
        f"# universe_tags={','.join(result.include_tags) or '(all)'}",
        f"# universe_exclude_tags={','.join(result.exclude_tags) or '(none)'}",
        f"# universe_size={result.universe_size}",
        f"# universe_membership_vintage={MEMBERSHIP_VINTAGE_NOTE}",
        f"# fill_convention={FILL_CONVENTION_NOTE}",
    ]
    lines.append(",".join(SIGNALS_COLUMNS))
    for row in sorted(result.rows, key=lambda r: r.symbol):
        lines.append(
            ",".join(
                [
                    row.symbol,
                    row.signal_date.isoformat(),
                    _fmt(row.close),
                    row.status,
                    row.last_entry_date.isoformat() if row.last_entry_date else "",
                    _fmt(row.last_entry_close),
                    row.last_exit_date.isoformat() if row.last_exit_date else "",
                    _fmt(row.last_exit_close),
                    str(row.days_since_entry) if row.days_since_entry is not None else "",
                    str(row.days_since_exit) if row.days_since_exit is not None else "",
                    str(row.n_bars),
                    _fmt(row.dist_lo),
                    _fmt(row.drawdown),
                    _fmt(row.vov_pct),
                    _fmt(row.above_fast),
                    _fmt(row.above_slow),
                    _fmt(row.mom_value),
                    _fmt(row.mom_rank),
                    _fmt(row.pullback_dist),
                    _fmt(row.gate),
                ]
            )
        )
    return "\n".join(lines) + "\n"
