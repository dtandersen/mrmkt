import datetime
from dataclasses import dataclass


@dataclass
class StockPrice:
    symbol: str
    date: datetime.date
    open: float
    high: float
    low: float
    close: float
    volume: float
