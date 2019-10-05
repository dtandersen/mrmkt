import datetime
from dataclasses import dataclass
from typing import List, Optional

from mrmkt.repo.provider import ReadOnlyMarketDataProvider, MarketDataProvider
from mrmkt.entity.stock_price import StockPrice


@dataclass
class PriceLoaderRequest:
    tickers: any = None
    start: Optional[datetime.date] = None
    end: Optional[datetime.date] = None


@dataclass
class PriceLoaderResult:
    lookup: any
    prices: List[StockPrice] = None


class PriceLoader:
    def __init__(self, source: ReadOnlyMarketDataProvider, dest: MarketDataProvider):
        self.source = source
        self.dest = dest

    def execute(self, request: PriceLoaderRequest, result: PriceLoaderResult) -> None:
        if request.tickers is None:
            tickers = self.source.tickers.get_symbols()
        elif isinstance(request.tickers, str):
            tickers = [request.tickers]
        elif isinstance(request.tickers, List):
            tickers = request.tickers
        else:
            tickers = []

        for ticker in tickers:
            current_prices = self.dest.prices.list_prices(symbol=ticker)
            if request.start is not None:
                start = request.start
            elif len(current_prices) > 0:
                start = current_prices[-1].date
            else:
                start = None

            result.lookup({
                "ticker": ticker,
                "start": start
            })

            prices = self.source.prices.list_prices(symbol=ticker, start=start, end=request.end)
            self.dest.prices.add_prices(prices)
