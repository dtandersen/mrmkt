import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from unittest import TestCase
from unittest.mock import Mock
from hamcrest import *
from tiingo import TiingoClient

from mrmkt.common.tiingorepo import TiingoPriceRepository
from mrmkt.common.util import to_date
from mrmkt.entity.stock_price import StockPrice


@dataclass
class TickerArgs:
    symbol: str
    startDate: Optional[str]
    endDate: Optional[str]


class MockTiingoClient(TiingoClient):
    # noinspection PyMissingConstructor
    def __init__(self):
        self.data = dict()

    def get_ticker_price(self, ticker,
                         startDate=None, endDate=None,
                         fmt='json', frequency='daily'):
        return self.data[str(TickerArgs(symbol=ticker, startDate=startDate, endDate=endDate))]


class TestTiingoGateway(TestCase):
    def setUp(self) -> None:
        self.client = MockTiingoClient()
        self.x = TiingoPriceRepository(self.client)

    def test_get_prices(self):
        self.load_data('AAPL', None, None, 'tiingo/AAPL-daily.json')

        prices = self.x.list_prices('AAPL')

        assert_that(prices, equal_to([
            StockPrice(
                symbol='AAPL',
                date=to_date("2019-07-12"),
                open=201.6773666733,
                high=203.2214512292,
                low=201.4283207772,
                close=202.5241227201,
                volume=17595212
            )
        ]))

    def test_get_goog(self):
        self.load_data('GOOG', "2019-10-03", "2019-10-04", 'tiingo/GOOG-daily.json')

        prices = self.x.list_prices('GOOG', start=to_date("2019-10-03"), end=to_date("2019-10-04"))

        assert_that(prices, equal_to([
            StockPrice(
                symbol='GOOG',
                date=to_date("2019-10-03"),
                open=1180.0,
                high=1189.06,
                low=1162.43,
                close=1187.83,
                volume=1663656
            ),
            StockPrice(
                symbol='GOOG',
                date=to_date("2019-10-04"),
                open=1191.89,
                high=1211.44,
                low=1189.17,
                close=1209.0,
                volume=1147871
            )
        ]))

    def load_data(self, ticker, start, end, file):
        self.client.data[str(TickerArgs(symbol=ticker, startDate=start, endDate=end))] = json.loads(
            Path(file).read_text())


def mock_responses(responses, default_response=None):
    return lambda input: responses[input] if input in responses else default_response
