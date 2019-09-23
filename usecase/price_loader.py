import datetime
from dataclasses import dataclass
from typing import List, Optional

from common.finrepo import FinancialRepository
from entity.stock_price import StockPrice


@dataclass
class PriceLoaderRequest:
    tickers: any = None
    start: Optional[datetime.date] = None
    end: Optional[datetime.date] = None


@dataclass
class PriceLoaderResult:
    prices: List[StockPrice]


class PriceLoader:
    def __init__(self, source: FinancialRepository, dest: FinancialRepository):
        self.source = source
        self.dest = dest

    def execute(self, request: PriceLoaderRequest) -> None:
        if request.tickers is None:
            tickers = self.source.get_symbols()
        elif isinstance(request.tickers, str):
            tickers = [request.tickers]
        else:
            tickers = []

        for ticker in tickers:
            current_prices = self.dest.list_prices(symbol=ticker)
            if request.start is not None:
                start = request.start
            elif len(current_prices) > 0:
                start = current_prices[-1].date
            else:
                start = None

            prices = self.source.list_prices(symbol=ticker, start=start, end=request.end)
            self.dest.add_prices(prices)