import datetime
from abc import abstractmethod, ABC
from typing import List

from mrmkt.common.sql import Duplicate
from mrmkt.entity.stock_price import StockPrice


class ReadOnlyPriceRepository(ABC):
    @abstractmethod
    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        pass

    @abstractmethod
    def list_prices(self, ticker: str, start: datetime.date = None, end: datetime.date = None) -> List[StockPrice]:
        """
        Return value is sorted
        """
        pass


class PriceRepository(ReadOnlyPriceRepository):
    @abstractmethod
    def add_price(self, price: StockPrice) -> None:
        pass

    def add_prices(self, prices: List[StockPrice]) -> None:
        for price in prices:
            try:
                self.add_price(price)
            except Duplicate:
                pass
