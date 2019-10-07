from unittest import TestCase
from hamcrest import *

from mrmkt.entity.ticker import Ticker
from mrmkt.usecase.fetch_tickers import FetchTickersUseCase, FetchTickersResult
from tests.testenv import TestEnvironment


class TestFetchTickers(TestCase):
    def setUp(self) -> None:
        self.env = TestEnvironment()

    def test_fetch_tickers(self):
        self.add_remote_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))
        self.add_remote_ticker(Ticker(ticker='MSFT', exchange='NYSE', type='Stock'))

        self.whenExecuted()

        assert_that(self.local_tickers(), equal_to([
            Ticker(ticker='SPY', exchange='ABC', type='ETF'),
            Ticker(ticker='MSFT', exchange='NYSE', type='Stock')
        ]))
        assert_that(self.ticker_count(), equal_to(2))

    def test_ignore_duplicate_ticker(self):
        self.add_remote_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))
        self.add_local_ticker(Ticker(ticker='SPY', exchange='ABC', type='ETF'))

        self.whenExecuted()

        assert_that(self.local_tickers(), equal_to([
            Ticker(ticker='SPY', exchange='ABC', type='ETF')
        ]))
        assert_that(self.ticker_count(), equal_to(1))

    def add_remote_ticker(self, ticker: Ticker):
        self.env.remote.tickers.add_ticker(ticker)

    def local_tickers(self):
        return self.env.local.tickers.get_tickers()

    def add_local_ticker(self, ticker: Ticker):
        self.env.local.tickers.add_ticker(ticker)

    def whenExecuted(self):
        cmd = FetchTickersUseCase(self.env.remote.tickers, self.env.local.tickers)
        self.result = FetchTickersResult(on_tickers_updated=self.on_tickers_updated)
        cmd.result = self.result
        cmd.execute()

    def on_tickers_updated(self, count: int):
        self.count = count

    def ticker_count(self):
        return self.count
