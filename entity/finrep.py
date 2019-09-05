import datetime
from dataclasses import dataclass

from entity.balance_sheet import BalanceSheet
from entity.cash_flow import CashFlow
from entity.income_statement import IncomeStatement


@dataclass
class FinancialReport:
    symbol: str
    date: datetime.date
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: CashFlow
