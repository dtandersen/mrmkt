from dataclasses import dataclass


@dataclass
class BalanceSheet:
    date: str
    symbol: str
    totalAssets: float
    totalLiabilities: float
