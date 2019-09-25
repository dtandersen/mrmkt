import datetime
from dataclasses import dataclass


@dataclass
class BalanceSheet:
    symbol: str
    date: datetime.date
    totalAssets: float
    totalLiabilities: float
    non_current_assets: float = -1
    inventories: float = -1
    receivables: float = -1
