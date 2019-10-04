from unittest import TestCase

from tiingo import TiingoClient

from mrmkt.common.tiingorepo import TingoGateway


class MockTiingoClient(TiingoClient):
    def get_ticker_price(self, ticker,
                         startDate=None, endDate=None,
                         fmt='json', frequency='daily'):
        pass


class TestTiingoGateway(TestCase):
    def test_get_prices(self):
        mock = MockTiingoClient()
        x = TingoGateway(mock)
        prices = x.list_prices('AAPL')