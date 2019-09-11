import datetime
from dataclasses import dataclass


@dataclass
class Analysis():
    symbol: str
    date: datetime.date
    netIncome: float
    buffetNumber: float
    priceToBookValue: float
    sharesOutstanding: float
    liabilities: float
    assets: float
    marginOfSafety: float
    bookValue: float
    eps: float
    equity: float
    pe: float
    current_assets: float = -1
