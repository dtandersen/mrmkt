import datetime
from dataclasses import dataclass


@dataclass
class EnterpriseValue:
    symbol: str
    date: datetime.date
    stock_price: float
    shares_outstanding: float
    market_cap: float
