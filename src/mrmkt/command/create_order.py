"""Paper-account order-create command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trading import TradingOrder


@dataclass(frozen=True)
class CreateOrderRequest:
    symbol: str
    side: str
    qty: float
    limit_price: float
    stop_price: float | None = None
    time_in_force: str = "day"


@dataclass
class CreateOrderResult(BaseResult[TradingOrder]):
    pass


class CreateOrder(Command[CreateOrderRequest, CreateOrderResult]):
    """Submit a GTC limit order (OTO stop-loss when stop given)."""

    def __init__(self, trading_gateway):
        self.trading_gateway = trading_gateway

    def execute(self, request: CreateOrderRequest) -> CreateOrderResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return CreateOrderResult.invalid_data([str(error)])
        side = (request.side or "").strip().lower()
        if side not in ("buy", "sell"):
            return CreateOrderResult.invalid_data(
                ["side must be 'buy' or 'sell' (use --buy/--sell)"]
            )
        errors: list[str] = []
        if request.qty is None or request.qty <= 0:
            errors.append("quantity must be > 0")
        if request.limit_price is None or request.limit_price <= 0:
            errors.append("limit price must be > 0")
        if request.stop_price is not None and request.stop_price <= 0:
            errors.append("stop price must be > 0")
        tif = (request.time_in_force or "day").strip().lower()
        if tif not in ("day", "gtc"):
            errors.append("time in force must be 'day' or 'gtc' (use --tif)")
        if request.stop_price is not None and request.limit_price is not None:
            if side == "buy" and request.stop_price >= request.limit_price:
                errors.append("buy stop must be below the limit price")
            if side == "sell" and request.stop_price <= request.limit_price:
                errors.append("sell stop must be above the limit price")
        if errors:
            return CreateOrderResult.invalid_data(errors)
        try:
            order = self.trading_gateway.submit_limit_order(
                symbol=symbol,
                side=side,
                qty=request.qty,
                limit_price=request.limit_price,
                stop_price=request.stop_price,
                time_in_force=tif,
            )
        except ValueError as error:
            return CreateOrderResult.invalid_data([str(error)])
        except Exception as error:
            return CreateOrderResult.error([f"Failed to create order: {error}"])
        return CreateOrderResult.success(order)
