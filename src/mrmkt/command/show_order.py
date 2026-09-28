"""Paper-account order-show command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trading import TradingOrder


@dataclass(frozen=True)
class ShowOrderRequest:
    order_id: str


@dataclass
class ShowOrderResult(BaseResult[TradingOrder]):
    pass


class ShowOrder(Command[ShowOrderRequest, ShowOrderResult]):
    """Return a single paper-account order by id."""

    def __init__(self, trading_gateway):
        self.trading_gateway = trading_gateway

    def execute(self, request: ShowOrderRequest) -> ShowOrderResult:
        order_id = (request.order_id or "").strip()
        if not order_id:
            return ShowOrderResult.invalid_data(["order id is required"])
        try:
            order = self.trading_gateway.get_order(order_id)
        except Exception as error:
            return ShowOrderResult.error([f"Failed to show order: {error}"])
        if order is None:
            return ShowOrderResult.not_found([f"no order with id {order_id!r}"])
        return ShowOrderResult.success(order)
