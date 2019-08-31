import datetime
from dataclasses import dataclass


@dataclass
class StockPrice:
    symbol: str
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
