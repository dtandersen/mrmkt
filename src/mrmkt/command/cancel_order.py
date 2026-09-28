"""Paper-account order-cancel command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trading import TradingOrder


@dataclass(frozen=True)
class CancelOrderRequest:
    order_id: str


@dataclass
class CancelOrderResult(BaseResult[TradingOrder]):
    pass


class CancelOrder(Command[CancelOrderRequest, CancelOrderResult]):
    """Cancel one open paper-account order by id."""

    def __init__(self, trading_gateway):
        self.trading_gateway = trading_gateway

    def execute(self, request: CancelOrderRequest) -> CancelOrderResult:
        order_id = (request.order_id or "").strip()
        if not order_id:
            return CancelOrderResult.invalid_data(["order id is required"])
        try:
            order = self.trading_gateway.get_order(order_id)
        except Exception as error:
            return CancelOrderResult.error([f"Failed to cancel order: {error}"])
        if order is None:
            return CancelOrderResult.not_found([f"no order with id {order_id!r}"])
        try:
            self.trading_gateway.cancel_order(order_id)
        except KeyError:
            return CancelOrderResult.not_found([f"no order with id {order_id!r}"])
        except Exception as error:
            return CancelOrderResult.error([f"Failed to cancel order: {error}"])
        return CancelOrderResult.success(order)
