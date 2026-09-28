"""Alpaca paper trading gateway (outer implementation).

Wraps ``TradingClient`` (paper endpoint only — enforced at client
construction in ``command._shared.create_alpaca_client``). Converts SDK
models to ``entity.trading`` dataclasses so commands stay SDK-free.
"""

from typing import Any

from alpaca.trading.enums import OrderClass, OrderSide, QueryOrderStatus, TimeInForce
from alpaca.trading.requests import (
    GetOrdersRequest,
    LimitOrderRequest,
    StopLossRequest,
)

from mrmkt.entity.trading import Account, Position, TradingOrder
from mrmkt.gateway import TradingGateway


def _value(value: Any) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _position_of(position: Any) -> Position:
    return Position(
        symbol=str(position.symbol),
        qty=float(position.qty),
        avg_entry_price=float(position.avg_entry_price),
        current_price=_number(getattr(position, "current_price", None)),
        market_value=_number(getattr(position, "market_value", None)),
        unrealized_pl=_number(getattr(position, "unrealized_pl", None)),
    )


def _account_of(account: Any) -> Account:
    equity = _number(getattr(account, "equity", None))
    cash = _number(getattr(account, "cash", None))
    buying_power = _number(getattr(account, "buying_power", None))
    if equity is None or cash is None or buying_power is None:
        raise ValueError("paper account is missing equity/cash/buying_power")
    return Account(
        equity=equity,
        cash=cash,
        buying_power=buying_power,
        portfolio_value=_number(getattr(account, "portfolio_value", None)),
        currency=str(getattr(account, "currency", "USD") or "USD"),
    )


def _order_of(order: Any) -> TradingOrder:
    return TradingOrder(
        id=str(order.id),
        symbol=str(order.symbol),
        side=_value(order.side) or "",
        qty=float(order.qty),
        order_type=_value(
            getattr(order, "order_type", None) or getattr(order, "type", None)
        )
        or "",
        status=_value(order.status) or "",
        limit_price=_number(getattr(order, "limit_price", None)),
        stop_price=_number(getattr(order, "stop_price", None)),
        filled_qty=_number(getattr(order, "filled_qty", None)),
        filled_avg_price=_number(getattr(order, "filled_avg_price", None)),
        time_in_force=_value(getattr(order, "time_in_force", None)),
    )


class AlpacaTradingGateway(TradingGateway):
    """TradingGateway over the Alpaca paper TradingClient."""

    def __init__(self, trading_client: Any):
        self.trading_client = trading_client

    def list_positions(self) -> list[Position]:
        positions = self.trading_client.get_all_positions()
        return sorted((_position_of(p) for p in positions), key=lambda h: h.symbol)

    def list_orders(self, status: str = "open") -> list[TradingOrder]:
        normalized = (status or "open").strip().lower()
        if normalized == "open":
            query_status = QueryOrderStatus.OPEN
        elif normalized == "closed":
            query_status = QueryOrderStatus.CLOSED
        else:
            query_status = QueryOrderStatus.ALL
        orders = self.trading_client.get_orders(
            filter=GetOrdersRequest(status=query_status, limit=500)
        )
        return sorted((_order_of(o) for o in orders), key=lambda o: o.symbol)

    def get_order(self, order_id: str) -> TradingOrder | None:
        try:
            order = self.trading_client.get_order_by_id(order_id)
        except Exception as error:
            message = str(error).lower()
            if "404" in message or "not found" in message:
                return None
            raise
        return _order_of(order)

    def submit_limit_order(
        self,
        symbol: str,
        side: str,
        qty: float,
        limit_price: float,
        stop_price: float | None = None,
        time_in_force: str = "day",
    ) -> TradingOrder:
        order_side = OrderSide.BUY if side == "buy" else OrderSide.SELL
        tif = (time_in_force or "day").strip().lower()
        if tif == "day":
            tif_enum = TimeInForce.DAY
        elif tif == "gtc":
            tif_enum = TimeInForce.GTC
        else:
            raise ValueError(
                f"time_in_force must be 'day' or 'gtc', got {time_in_force!r}"
            )
        kwargs: dict[str, Any] = {
            "symbol": symbol,
            "qty": qty,
            "side": order_side,
            "time_in_force": tif_enum,
            "limit_price": limit_price,
        }
        if stop_price is not None:
            kwargs["order_class"] = OrderClass.OTO
            kwargs["stop_loss"] = StopLossRequest(stop_price=stop_price)
        request = LimitOrderRequest(**kwargs)
        return _order_of(self.trading_client.submit_order(request))

    def cancel_order(self, order_id: str) -> None:
        try:
            self.trading_client.cancel_order_by_id(order_id)
        except Exception as error:
            message = str(error).lower()
            if "404" in message or "not found" in message:
                raise KeyError(order_id) from error
            raise

    def get_account(self) -> Account:
        return _account_of(self.trading_client.get_account())
