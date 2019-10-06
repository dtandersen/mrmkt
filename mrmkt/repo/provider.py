from mrmkt.repo.financials import FinancialRepository, ReadOnlyFinancialRepository
from mrmkt.repo.prices import PriceRepository, ReadOnlyPriceRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository


class ReadOnlyMarketDataProvider:
    def __init__(self, financials: ReadOnlyFinancialRepository, prices: ReadOnlyPriceRepository,
                 tickers: ReadOnlyTickerRepository):
        self.tickers = tickers
        self.prices = prices
        self.financials = financials


class MarketDataProvider(ReadOnlyMarketDataProvider):
    def __init__(self, financials: FinancialRepository, prices: PriceRepository, tickers: ReadOnlyTickerRepository):
        super().__init__(financials, prices, tickers)
        # self.tickers = tickers
        # self.prices = prices
        # self.financials = financials
        # print(self.financials)
