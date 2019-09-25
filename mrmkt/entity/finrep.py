import datetime
from dataclasses import dataclass
from typing import Optional, List

from mrmkt.entity.balance_sheet import BalanceSheet
from mrmkt.entity.cash_flow import CashFlow
from mrmkt.entity.enterprise_value import EnterpriseValue
from mrmkt.entity.income_statement import IncomeStatement


@dataclass
class FinancialReport:
    symbol: str
    date: datetime.date
    income_statement: IncomeStatement
    balance_sheet: BalanceSheet
    cash_flow: Optional[CashFlow]
    enterprise_value: EnterpriseValue


@dataclass
class FinancialReports:
    symbol: str
    financial_reports: List[FinancialReport]
