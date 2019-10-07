from mrmkt.repo.financials import FinancialRepository, ReadOnlyFinancialRepository
from mrmkt.repo.prices import PriceRepository, ReadOnlyPriceRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository, TickerRepository


class ReadOnlyMarketDataProvider:
    def __init__(self, financials: ReadOnlyFinancialRepository, prices: ReadOnlyPriceRepository,
                 tickers: ReadOnlyTickerRepository):
        self._tickers = tickers
        self.prices = prices
        self.financials = financials

    @property
    def tickers(self) -> ReadOnlyTickerRepository:
        return self._tickers


class MarketDataProvider(ReadOnlyMarketDataProvider):
    # noinspection PyMissingConstructor
    def __init__(self, financials: FinancialRepository, prices: PriceRepository, tickers: TickerRepository):
        self._tickers = tickers
        self.prices = prices
        self.financials = financials

    @property
    def tickers(self) -> TickerRepository:
        return self._tickers
