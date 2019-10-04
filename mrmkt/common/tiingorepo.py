import datetime
from typing import List

from tiingo import TiingoClient

from mrmkt.entity.stock_price import StockPrice
from mrmkt.repo.prices import ReadOnlyPriceRepository


class TingoGateway(ReadOnlyPriceRepository):
    def __init__(self, client: TiingoClient):
        self.client = client
    
    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        raise NotImplementedError

    def list_prices(self, symbol: str, start: datetime.date = None, end: datetime.date = None) -> List[StockPrice]:
        pass
