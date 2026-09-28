"""Paper-account position-list command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trading import Position


@dataclass(frozen=True)
class ListPositionsRequest:
    pass


@dataclass
class ListPositionsResult(BaseResult[list[Position]]):
    pass


class ListPositions(Command[ListPositionsRequest, ListPositionsResult]):
    """List open paper-account positions in symbol order."""

    def __init__(self, trading_gateway):
        self.trading_gateway = trading_gateway

    def execute(self, request: ListPositionsRequest) -> ListPositionsResult:
        try:
            positions = self.trading_gateway.list_positions()
        except Exception as error:
            return ListPositionsResult.error([f"Failed to list positions: {error}"])
        return ListPositionsResult.success(positions)
