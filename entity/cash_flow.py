import datetime
from dataclasses import dataclass


@dataclass
class CashFlow:
    symbol: str
    date: datetime.date
    operating_cash_flow: float
    capital_expenditure: float
    free_cash_flow: float
    dividend_payments: float
