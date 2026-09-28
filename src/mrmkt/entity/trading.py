"""Live-trading entities (returned by trading gateways).

Separate from ``entity.broker``: ``MockBroker``/``Order`` there are
backtest-only (PENDING→FULFILLED, no prices). These carry the Alpaca
paper-account fields the order/position CLI renders.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Position:
    """One open paper-account position."""

    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float | None = None
    market_value: float | None = None
    unrealized_pl: float | None = None


@dataclass(frozen=True)
class Account:
    """Paper-account balance snapshot."""

    equity: float
    cash: float
    buying_power: float
    portfolio_value: float | None = None
    currency: str = "USD"


@dataclass(frozen=True)
class TradingOrder:
    """One paper-account order (open or closed)."""

    id: str
    symbol: str
    side: str
    qty: float
    order_type: str
    status: str
    limit_price: float | None = None
    stop_price: float | None = None
    filled_qty: float | None = None
    filled_avg_price: float | None = None
    time_in_force: str | None = None
