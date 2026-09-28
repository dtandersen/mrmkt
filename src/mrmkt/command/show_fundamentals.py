"""Stored fundamentals-show command."""

from dataclasses import dataclass

from mrmkt.command._shared import normalize_symbol
from mrmkt.command.base import BaseResult, Command


@dataclass(frozen=True)
class ShowFundamentalsRequest:
    symbol: str


@dataclass(frozen=True)
class FundamentalsView:
    """One symbol's stored statements; each list is date-ordered."""

    symbol: str
    incomes: tuple = ()
    balances: tuple = ()
    cashflows: tuple = ()
    enterprise_values: tuple = ()


@dataclass
class ShowFundamentalsResult(BaseResult[FundamentalsView]):
    pass


class ShowFundamentals(Command[ShowFundamentalsRequest, ShowFundamentalsResult]):
    """Return stored fundamentals for one symbol in deterministic order."""

    def __init__(self, financials):
        self.financials = financials

    def execute(self, request: ShowFundamentalsRequest) -> ShowFundamentalsResult:
        try:
            symbol = normalize_symbol(request.symbol)
        except ValueError as error:
            return ShowFundamentalsResult.invalid_data([str(error)])
        try:
            incomes = sorted(
                self.financials.list_income_statements(symbol),
                key=lambda item: item.date,
            )
            balances = sorted(
                self.financials.list_balance_sheets(symbol),
                key=lambda item: item.date,
            )
            cashflows = sorted(
                self.financials.list_cash_flows(symbol),
                key=lambda item: item.date,
            )
            enterprise_values = sorted(
                self.financials.list_enterprise_value(symbol),
                key=lambda item: item.date,
            )
        except Exception as error:
            return ShowFundamentalsResult.error(
                [f"Failed to show fundamentals: {error}"]
            )
        if not (incomes or balances or cashflows or enterprise_values):
            return ShowFundamentalsResult.not_found([f"no fundamentals for {symbol!r}"])
        return ShowFundamentalsResult.success(
            FundamentalsView(
                symbol=symbol,
                incomes=tuple(incomes),
                balances=tuple(balances),
                cashflows=tuple(cashflows),
                enterprise_values=tuple(enterprise_values),
            )
        )
