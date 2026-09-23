"""VectorBT execution engine with an explicit portfolio overlay.

One wide ``from_signals`` call simulates fills (close execution,
intrabar stop-loss, percentage fees) and produces trade records.
Selection, position caps, the equal-weight daily series, and statistics
use the same transparent overlay math as the validated research engine:
sizing scale is irrelevant because the overlay weights by return.
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
    records = simulate_fills(close, entries, exits, size_pct, fees, stop, freq, high, low)
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


def aggregate_trades(
    close: pd.DataFrame,
    records: pd.DataFrame,
    max_positions: int,
    fees_per_side: float = FEES_PER_SIDE,
) -> PortfolioResult:
    """Chronological cap-sweep plus equal-weight daily series and stats."""
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
            if row["Status"] == "Closed":
                exit_day = row["Exit Timestamp"]
                g1 = day_of.get(exit_day)
                if g1 is None:
                    continue
                span = g1 - g0
                if span <= 0:
                    continue
                marks = prices[l0 + 1 : l0 + span + 1] / prices[l0 : l0 + span] - 1
                day_sum[g0 + 1 : g1 + 1] += marks
                # Attribute each side's friction to a day the position is
                # counted open (entry fee to the first marked day, exit fee
                # to the exit day): booking at g0 would drop the fee when
                # nothing else is open there, or spread it over incumbents
                # excluding the entrant.
                day_cost[g0 + 1] += fees_per_side
                day_cost[g1] += fees_per_side
                open_count[g0 + 1 : g1 + 1] += 1
                opened_today += 1
                gross = float(row["Avg Exit Price"] / row["Avg Entry Price"] - 1)
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
                if span <= 0:
                    continue
                marks = prices[l0 + 1 :] / prices[l0:-1] - 1
                day_sum[g0 + 1 :] += marks
                day_cost[g0 + 1] += fees_per_side
                open_count[g0 + 1 :] += 1
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
            profit_factor=float(wins.sum() / -losses.sum()) if len(losses) and losses.sum() else 0.0,
            expectancy=float(nets.mean()) if n_trades else 0.0,
            avg_hold_days=float(holds.mean()) if n_trades else 0.0,
            exposure=float(invested.mean()),
            trades=trades,
        )
    except (KeyError, AttributeError, IndexError, ValueError) as error:
        raise ValueError(f"failed to aggregate backtest portfolio: {error}") from error
