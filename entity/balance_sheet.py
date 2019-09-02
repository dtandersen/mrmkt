import datetime
from dataclasses import dataclass


@dataclass
class BalanceSheet:
    symbol: str
    date: datetime.date
    totalAssets: float
    totalLiabilities: float
