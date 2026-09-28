"""Paper-account order-list command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trading import TradingOrder

STATUSES = ("open", "closed", "all")


@dataclass(frozen=True)
class ListOrdersRequest:
    status: str = "open"


@dataclass
class ListOrdersResult(BaseResult[list[TradingOrder]]):
    pass


class ListOrders(Command[ListOrdersRequest, ListOrdersResult]):
    """List paper-account orders (default: open only)."""

    def __init__(self, trading_gateway):
        self.trading_gateway = trading_gateway

    def execute(self, request: ListOrdersRequest) -> ListOrdersResult:
        normalized = (request.status or "open").strip().lower()
        if normalized not in STATUSES:
            return ListOrdersResult.invalid_data(
                ["status must be one of: open, closed, all"]
            )
        try:
            orders = self.trading_gateway.list_orders(status=normalized)
        except Exception as error:
            return ListOrdersResult.error([f"Failed to list orders: {error}"])
        return ListOrdersResult.success(orders)
