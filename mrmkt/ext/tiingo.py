import datetime
from typing import List

from tiingo import TiingoClient
from tiingo.restclient import RestClientError

from mrmkt.common.util import to_date, to_iso
from mrmkt.entity.stock_price import StockPrice
from mrmkt.entity.ticker import Ticker
from mrmkt.repo.prices import ReadOnlyPriceRepository
from mrmkt.repo.tickers import ReadOnlyTickerRepository


class TiingoPriceRepository(ReadOnlyPriceRepository, ReadOnlyTickerRepository):
    def __init__(self, tiingo: TiingoClient):
        self.tiingo = tiingo

    def get_price_on_or_after(self, symbol: str, date: datetime.date) -> StockPrice:
        raise NotImplementedError

    def list_prices(self, ticker: str, start: datetime.date = None, end: datetime.date = None) -> List[StockPrice]:
        start_iso = None
        end_iso = None

        if start is not None:
            start_iso = to_iso(start)

        if end is not None:
            end_iso = to_iso(end)

        try:
            prices = self.tiingo.get_ticker_price(ticker, start_iso, end_iso)
            return list(map(lambda x: TiingoPriceRepository.map_price(x, ticker), prices))
        except RestClientError:
            return []

    @staticmethod
    def map_price(json, ticker):
        return StockPrice(
            symbol=ticker,
            date=to_date(json['date'][0:10]),
            open=json['adjOpen'],
            high=json['adjHigh'],
            low=json['adjLow'],
            close=json['adjClose'],
            volume=json['volume']
        )

    def get_tickers(self) -> List[Ticker]:
        tickers = []

        for ticker in self.tiingo.list_stock_tickers():
            tickers.append(self.map_ticker(ticker))

        for ticker in self.tiingo.list_etf_tickers():
            tickers.append(self.map_ticker(ticker))

        for ticker in self.tiingo.list_fund_tickers():
            tickers.append(self.map_ticker(ticker))

        return tickers

    def map_ticker(self, ticker: dict) -> Ticker:
        return Ticker(
            ticker=ticker['ticker'],
            exchange=ticker['exchange'],
            type=ticker['assetType']
        )

    def get_symbols(self) -> List[str]:
        raise NotImplementedError
