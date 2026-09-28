from abc import ABC, abstractmethod

from mrmkt.entity.ticker import Ticker


class ReadOnlyTickerRepository(ABC):
    @abstractmethod
    def get_symbols(self) -> list[str]:
        pass

    @abstractmethod
    def get_tickers(self) -> list[Ticker]:
        pass

    def list_tickers_by_symbol(self, symbol: str) -> list[Ticker]:
        """Return listings for one symbol.

        Backends can override this with an indexed lookup; the default keeps
        existing read-only implementations compatible.
        """
        normalized = symbol.strip().upper()
        return [ticker for ticker in self.get_tickers() if ticker.ticker == normalized]


class TickerRepository(ReadOnlyTickerRepository):
    @abstractmethod
    def add_ticker(self, ticker: Ticker):
        pass
