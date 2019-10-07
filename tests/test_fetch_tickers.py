from unittest import TestCase
from hamcrest import *

from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.fetch_tickers import FetchTickersUseCase
from tests.testenv import TestEnvironment


class TestFetchTickers(TestCase):
    def setUp(self) -> None:
        self.env = TestEnvironment()

    def test_fetch_tickers(self):
        self.add_remote_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))
        self.add_remote_ticker(Ticker(ticker='MSFT', exchange='NYSE', type='Stock'))

        cmd = FetchTickersUseCase(self.env.remote.tickers, self.env.local.tickers)
        cmd.execute()

        assert_that(self.local_ticker('SPY', 'ABC'), equal_to([
            Ticker(ticker='SPY', exchange='ABC', type='ETF'),
            Ticker(ticker='MSFT', exchange='NYSE', type='Stock')
        ]))

    def test_ignore_duplicate_ticker(self):
        self.add_remote_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))
        self.add_local_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))

        cmd = FetchTickersUseCase(self.env.remote.tickers, self.env.local.tickers)
        cmd.execute()

        assert_that(self.local_ticker('SPY', 'ABC'), equal_to([
            Ticker(ticker='SPY', exchange='ABC', type='ETF')
        ]))

    def add_remote_ticker(self, ticker: Ticker):
        self.env.remote.tickers.add_ticker(ticker)

    def local_ticker(self, param, param1):
        return self.env.local.tickers.get_tickers()

    def add_local_ticker(self, ticker: Ticker):
        self.env.local.tickers.add_ticker(ticker)
