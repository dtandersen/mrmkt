from unittest import TestCase

from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.fetch_tickers import FetchTickersUseCase
from tests.testenv import TestEnvironment


class TestFetchTickers(TestCase):
    def setUp(self) -> None:
        self.env = TestEnvironment()

    # def test_fetch_tickers(self):
    #     self.add_remote_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))
    #     cmd = FetchTickersUseCase(self.env.remote.tickers, self.env.local.tickers)
    #     cmd.execute()

    def add_remote_ticker(self, ticker: Ticker):
        self.env.remote.tickers.add_ticker(ticker)
