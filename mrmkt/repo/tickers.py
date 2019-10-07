from abc import ABC, abstractmethod, ABCMeta
from typing import List

from mrmkt.entity.ticker import Ticker


class ReadOnlyTickerRepository(ABC):
    @abstractmethod
    def get_symbols(self) -> List[str]:
        pass

    @abstractmethod
    def get_tickers(self) -> List[Ticker]:
        pass


class TickerRepository(ReadOnlyTickerRepository):
    @abstractmethod
    def add_ticker(self, ticker: Ticker):
        pass
