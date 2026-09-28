"""Paper-account balance-show command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.entity.trading import Account


@dataclass(frozen=True)
class ShowBalanceRequest:
    pass


@dataclass
class ShowBalanceResult(BaseResult[Account]):
    pass


class ShowBalance(Command[ShowBalanceRequest, ShowBalanceResult]):
    """Return the paper-account balance snapshot."""

    def __init__(self, trading_gateway):
        self.trading_gateway = trading_gateway

    def execute(self, request: ShowBalanceRequest) -> ShowBalanceResult:
        try:
            account = self.trading_gateway.get_account()
        except Exception as error:
            return ShowBalanceResult.error([f"Failed to show balance: {error}"])
        return ShowBalanceResult.success(account)
