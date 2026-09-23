import datetime
from dataclasses import dataclass


@dataclass
class IncomeStatement:
    symbol: str
    date: datetime.date
    netIncome: float
    waso: int
    consolidated_net_income: float
