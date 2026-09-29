"""VectorBT execution engine with an explicit portfolio overlay.

One wide ``from_signals`` call simulates fills (next-bar-close execution
by default, intrabar stop-loss, all-in friction per side) and produces
trade records. Selection, position caps, the equal-weight daily series,
and statistics use a transparent overlay: sizing scale is irrelevant
because the overlay weights by return, so ``size_pct`` only sizes the
unconstrained fill simulation and never the reported portfolio weights
(validation plan open item — do not read position sizing into results).
Days a name has no stored price book no mark but keep the position
counted open; the valid-to-valid change lands when prices resume, so
gaps never erase P/L or free cap slots.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import vectorbt as vbt

FEES_PER_SIDE = 0.0


@dataclass
class TradeSummary:
    symbol: str
    entry_date: object
    exit_date: object | None
    gross_return: float
    hold_days: int


@dataclass
class PortfolioResult:
    total_return: float
    cagr: float
    sharpe: float
    max_drawdown: float
    n_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    expectancy: float
    avg_hold_days: float
    exposure: float
    trades: list = field(default_factory=list)


def run_portfolio(
    close: pd.DataFrame,
    entries: pd.DataFrame,
    exits: pd.DataFrame,
    size_pct: float = 2.0,
    fees: float = 0.0,
    stop: float = 0.08,
    max_positions: int = 50,
    freq: str = "1D",
    high: pd.DataFrame | None = None,
    low: pd.DataFrame | None = None,
) -> PortfolioResult:
    """Run a long-only signal portfolio over pre-sliced test windows.

    ``close``/``entries``/``exits`` must already start at the test window
    (warm-up history excluded) with aligned indexes and columns. Capital
    is effectively unconstrained inside the fill simulation; the overlay
    enforces ``max_positions`` equal-weight selection chronologically and
    accrues a flat fee per side on entry/exit days.
    """
    if close.empty or entries.empty or exits.empty:
        raise ValueError("close, entries, and exits must be non-empty")
    if not (close.index.equals(entries.index) and close.index.equals(exits.index)):
        raise ValueError("close, entries, and exits must share an index")
    if not (list(close.columns) == list(entries.columns) == list(exits.columns)):
        raise ValueError("close, entries, and exits must share columns")
    if not 0 < size_pct <= 100:
        raise ValueError("size_pct must be between 0 and 100")
    if not 0 < stop < 1:
        raise ValueError("stop must be between 0 and 1")
    if fees < 0:
        raise ValueError("fees must be >= 0")
    records = simulate_fills(
        close, entries, exits, size_pct, fees, stop, freq, high, low
    )
    return aggregate_trades(close, records, max_positions, fees)


def simulate_fills(
    close: pd.DataFrame,
    entries: pd.DataFrame,
    exits: pd.DataFrame,
    size_pct: float = 2.0,
    fees: float = 0.0,
    stop: float = 0.08,
    freq: str = "1D",
    high: pd.DataFrame | None = None,
    low: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Simulate fills for one signal set; returns vectorbt trade records.

    Capital is effectively unconstrained so every signal fills; selection
    happens later in :func:`aggregate_trades`. Frames must be aligned."""
    if not 0 < size_pct <= 100:
        raise ValueError("size_pct must be between 0 and 100")
    if not 0 < stop < 1:
        raise ValueError("stop must be between 0 and 1")
    if fees < 0:
        raise ValueError("fees must be >= 0")
    if close.empty or entries.empty or exits.empty:
        raise ValueError("close, entries, and exits must be non-empty")
    if not (close.index.equals(entries.index) and close.index.equals(exits.index)):
        raise ValueError("close, entries, and exits must share an index")
    if not (list(close.columns) == list(entries.columns) == list(exits.columns)):
        raise ValueError("close, entries, and exits must share columns")
    pf = vbt.Portfolio.from_signals(
        close,
        entries,
        exits,
        size_type="percent",
        size=size_pct,
        fees=fees,
        sl_stop=stop,
        init_cash=1e12,
        freq=freq,
        high=high,
        low=low,
    )
    # vectorbt stubs type .trades as a method; at runtime it is the
    # ExitTrades accessor (verified), so ignore the attr-defined error.
    return pf.trades.records_readable  # type: ignore[attr-defined]


def simulate_limit_touch_fills(
    close: pd.DataFrame,
    high: pd.DataFrame,
    low: pd.DataFrame,
    entries: pd.DataFrame,
    exits: pd.DataFrame,
    limits: pd.DataFrame,
    fill_lag: int,
    stop: float,
) -> pd.DataFrame:
    """Simulate resting-limit fills with stops on the true fill basis.

    ``entries``/``exits`` are post-lag fill-bar masks; ``limits`` holds the
    resting limits known at each signal bar. A kept entry fills at its
    limit (NaN limit = market fill at the fill-bar close). The stop
    anchors to that actual fill — not the fill-bar close — so an intrabar
    stop-out is priced off what the order really paid. Each bar, a stop
    trigger wins ties against a strategy exit on the same bar. Like
    :func:`simulate_fills`, capital is unconstrained and selection happens
    later in :func:`aggregate_trades`; records share its schema. Entries
    while already holding are ignored (no pyramiding), mirroring the
    close-fill path.
    """
    if not 0 < stop < 1:
        raise ValueError("stop must be between 0 and 1")
    if fill_lag not in (0, 1):
        raise ValueError("fill_lag must be 0 (signal close) or 1 (next close)")
    ref = limits.shift(fill_lag)
    columns = [
        "Entry Timestamp",
        "Exit Timestamp",
        "Status",
        "Avg Entry Price",
        "Avg Exit Price",
        "Column",
    ]
    rows: list = []
    for col in entries.columns:
        entry_mask = entries[col].fillna(False).to_numpy(dtype=bool)
        exit_mask = exits[col].fillna(False).to_numpy(dtype=bool)
        closes = np.asarray(pd.to_numeric(close[col], errors="coerce"), dtype=float)
        lows = np.asarray(pd.to_numeric(low[col], errors="coerce"), dtype=float)
        lims = np.asarray(pd.to_numeric(ref[col], errors="coerce"), dtype=float)
        stamps = entries.index.to_numpy()
        holding: tuple | None = None
        for pos in range(len(stamps)):
            if holding is not None:
                stop_px = holding[1] * (1 - stop)
                if np.isfinite(lows[pos]) and lows[pos] <= stop_px:
                    rows.append(
                        {
                            "Entry Timestamp": holding[0],
                            "Exit Timestamp": stamps[pos],
                            "Status": "Closed",
                            "Avg Entry Price": holding[1],
                            "Avg Exit Price": stop_px,
                            "Column": str(col),
                        }
                    )
                    holding = None
                    continue
                exit_px = _nonzero_number(closes[pos])
                if exit_mask[pos] and exit_px is not None:
                    rows.append(
                        {
                            "Entry Timestamp": holding[0],
                            "Exit Timestamp": stamps[pos],
                            "Status": "Closed",
                            "Avg Entry Price": holding[1],
                            "Avg Exit Price": exit_px,
                            "Column": str(col),
                        }
                    )
                    holding = None
                    continue
            if holding is None and entry_mask[pos]:
                price = _nonzero_number(lims[pos])
                if price is None:
                    price = _nonzero_number(closes[pos])
                if price is None:
                    continue
                holding = (stamps[pos], price)
        if holding is not None:
            rows.append(
                {
                    "Entry Timestamp": holding[0],
                    "Exit Timestamp": pd.NaT,
                    "Status": "Open",
                    "Avg Entry Price": holding[1],
                    "Avg Exit Price": np.nan,
                    "Column": str(col),
                }
            )
    if not rows:
        return pd.DataFrame({key: [] for key in columns})
    records = pd.DataFrame(rows, columns=columns)
    records["Entry Timestamp"] = pd.to_datetime(records["Entry Timestamp"])
    records["Exit Timestamp"] = pd.to_datetime(records["Exit Timestamp"])
    return records


def _book_holding(
    prices,
    l0: int,
    g0: int,
    span: int,
    day_sum,
    open_count,
    exit_px: float | None = None,
    entry_px: float | None = None,
) -> None:
    """Book one holding window with gap-bridged marks and full occupancy.

    Every day of the window counts open (a held position keeps its cap
    slot even when its series has no bar). Each valid close books its
    change since the last valid close on its own day, so P/L across a
    data gap lands when prices resume instead of vanishing. When
    ``exit_px`` is given, the final mark pins to the actual exit fill
    (intrabar stops) relative to the last valid close. When ``entry_px``
    is given (resting-limit fills priced away from the entry-bar close),
    the first mark compounds from the fill price instead.
    """
    prev_px: float | None = _nonzero_number(entry_px)
    if prev_px is None:
        prev_px = _nonzero_number(prices[l0])
    for k in range(1, span + 1):
        px = prices[l0 + k]
        open_count[g0 + k] += 1
        if k == span and exit_px is not None and np.isfinite(exit_px):
            # The exit fill is real even when the exit-day close is
            # missing (e.g. an intrabar stop on a gapped bar): pin it to
            # the last valid close instead of dropping the pin with the NaN.
            if prev_px is not None and prev_px != 0:
                mark = exit_px / prev_px - 1
                if np.isfinite(mark):
                    day_sum[g0 + k] += mark
            continue
        if not np.isfinite(px):
            continue
        if prev_px is not None and prev_px != 0:
            mark = px / prev_px - 1
            if np.isfinite(mark):
                day_sum[g0 + k] += mark
        prev_px = _nonzero_number(px) or prev_px


def _nonzero_number(value) -> float | None:
    """Finite nonzero float, else None (guards mark arithmetic)."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(result) or result == 0:
        return None
    return result


def _lookup_entry_price(entry_prices, sym, entry_day) -> float | None:
    """Actual entry fill for a resting-limit fill, else None (use Avg Entry)."""
    if not entry_prices:
        return None
    try:
        return _nonzero_number(entry_prices[(str(sym), entry_day)])
    except KeyError:
        return None


def aggregate_trades(
    close: pd.DataFrame,
    records: pd.DataFrame,
    max_positions: int,
    fees_per_side: float = FEES_PER_SIDE,
    entry_prices: dict | None = None,
) -> PortfolioResult:
    """Chronological cap-sweep plus equal-weight daily series and stats.

    ``entry_prices`` optionally maps ``(symbol, entry_timestamp)`` to the
    actual entry fill price (resting-limit fills); gross returns and first
    marks compound from it instead of the entry-bar close.
    """
    if fees_per_side < 0:
        raise ValueError("fees must be >= 0")
    try:
        day_of = {day: pos for pos, day in enumerate(close.index)}
        n_days = len(close.index)
        open_count = np.zeros(n_days, dtype=int)
        day_sum = np.zeros(n_days)
        day_cost = np.zeros(n_days)
        trades: list = []
        order = np.argsort(records["Entry Timestamp"].to_numpy(), kind="stable")
        cur_day = None
        opened_today = 0
        for loc in order:
            row = records.iloc[loc]
            sym = row["Column"]
            entry_day = row["Entry Timestamp"]
            g0 = day_of.get(entry_day)
            if g0 is None:
                continue
            if entry_day != cur_day:
                cur_day, opened_today = entry_day, 0
            if open_count[g0] + opened_today >= max_positions:
                continue
            prices = close[sym].to_numpy()
            l0 = int(np.searchsorted(close.index.to_numpy(), np.datetime64(entry_day)))
            entry_px = _lookup_entry_price(entry_prices, sym, entry_day)
            if row["Status"] == "Closed":
                exit_day = row["Exit Timestamp"]
                g1 = day_of.get(exit_day)
                if g1 is None:
                    continue
                span = g1 - g0
                if span < 0:
                    continue
                if span == 0:
                    # Same-bar round trip (e.g. an intrabar stop): no
                    # close-to-close marks exist, so book the actual fill
                    # prices plus both fees to the entry day. Dropping the
                    # record here silently erases the trade from the equity
                    # curve AND the trade stats.
                    entry_base = (
                        entry_px
                        if entry_px is not None
                        else float(row["Avg Entry Price"])
                    )
                    gross = float(row["Avg Exit Price"] / entry_base - 1)
                    day_sum[g0] += gross
                    day_cost[g0] += 2 * fees_per_side
                    open_count[g0] += 1
                    opened_today += 1
                    trades.append(
                        TradeSummary(
                            symbol=str(sym),
                            entry_date=entry_day,
                            exit_date=exit_day,
                            gross_return=gross,
                            hold_days=0,
                        )
                    )
                    continue
                try:
                    exit_px = float(row["Avg Exit Price"])
                except (TypeError, ValueError):
                    exit_px = None
                _book_holding(
                    prices, l0, g0, span, day_sum, open_count, exit_px, entry_px
                )
                # Attribute each side's friction to a day the position is
                # counted open (entry fee to the first marked day, exit fee
                # to the exit day): booking at g0 would drop the fee when
                # nothing else is open there, or spread it over incumbents
                # excluding the entrant.
                day_cost[g0 + 1] += fees_per_side
                day_cost[g1] += fees_per_side
                opened_today += 1
                entry_base = (
                    entry_px if entry_px is not None else float(row["Avg Entry Price"])
                )
                gross = float(row["Avg Exit Price"] / entry_base - 1)
                trades.append(
                    TradeSummary(
                        symbol=str(sym),
                        entry_date=entry_day,
                        exit_date=exit_day,
                        gross_return=gross,
                        hold_days=span,
                    )
                )
            else:
                span = n_days - 1 - g0
                if span < 0:
                    continue
                if span == 0:
                    # Opened on the final bar: no subsequent marks exist,
                    # but the entry fee was paid. Book it to the entry day
                    # with the position counted open so the fee is not lost.
                    day_cost[g0] += fees_per_side
                    open_count[g0] += 1
                    opened_today += 1
                    continue
                _book_holding(prices, l0, g0, span, day_sum, open_count, None, entry_px)
                day_cost[g0 + 1] += fees_per_side
                opened_today += 1
        invested = open_count > 0
        count = np.where(invested, open_count, 1)
        rets = np.where(invested, day_sum / count - day_cost / count, 0.0)
        # np.asarray pins the float-ndarray type through stub overloads.
        daily_values = np.asarray(rets, dtype=float)
        daily = pd.Series(daily_values, index=close.index)
        equity = (1 + daily).cumprod()
        n = len(daily)
        total = float(equity.iloc[-1] - 1) if n else 0.0
        cagr = float(equity.iloc[-1] ** (252 / n) - 1) if n else 0.0
        std = float(daily_values.std(ddof=1))
        sharpe = float(daily.mean() / std * (252**0.5)) if std else 0.0
        max_dd = float((equity / equity.cummax() - 1).min()) if n else 0.0
        nets = np.array([t.gross_return - 2 * fees_per_side for t in trades])
        wins = nets[nets > 0]
        losses = nets[nets <= 0]
        n_trades = len(trades)
        holds = np.array([t.hold_days for t in trades])
        return PortfolioResult(
            total_return=total,
            cagr=cagr,
            sharpe=sharpe,
            max_drawdown=max_dd,
            n_trades=n_trades,
            win_rate=float(len(wins) / n_trades) if n_trades else 0.0,
            avg_win=float(wins.mean()) if len(wins) else 0.0,
            avg_loss=float(losses.mean()) if len(losses) else 0.0,
            profit_factor=float(wins.sum() / -losses.sum())
            if len(losses) and losses.sum()
            else 0.0,
            expectancy=float(nets.mean()) if n_trades else 0.0,
            avg_hold_days=float(holds.mean()) if n_trades else 0.0,
            exposure=float(invested.mean()),
            trades=trades,
        )
    except (KeyError, AttributeError, IndexError, ValueError) as error:
        raise ValueError(f"failed to aggregate backtest portfolio: {error}") from error
