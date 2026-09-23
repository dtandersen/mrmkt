from abc import ABC, abstractmethod

from mrmkt.entity.ticker import Ticker


class TickerTagRepository(ABC):
    @abstractmethod
    def add_tag(self, ticker: str, exchange: str, tag: str) -> None:
        pass

    @abstractmethod
    def remove_tag(self, ticker: str, exchange: str, tag: str) -> bool:
        pass

    @abstractmethod
    def get_tags(self, ticker: str, exchange: str) -> list[str]:
        pass

    @abstractmethod
    def list_tickers_by_tag(self, tag: str) -> list[Ticker]:
        pass

    @abstractmethod
    def get_symbols_by_tag(self, tag: str) -> list[str]:
        pass
