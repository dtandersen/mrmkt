from unittest import TestCase

from hamcrest import assert_that, equal_to

from mrmkt.entity.ticker import Ticker
from mrmkt.command.import_symbols import ImportSymbols, ImportSymbolsRequest
from tests.testenv import TestEnvironment


class TestImportSymbols(TestCase):
    def setUp(self) -> None:
        self.env = TestEnvironment()

    def test_import_symbols(self):
        self.add_remote_ticker(Ticker(ticker="SPY", exchange="ABC", type="ETF"))
        self.add_remote_ticker(Ticker(ticker="MSFT", exchange="NYSE", type="Stock"))

        self.whenExecuted()

        assert_that(
            self.local_tickers(),
            equal_to(
                [
                    Ticker(ticker="SPY", exchange="ABC", type="ETF"),
                    Ticker(ticker="MSFT", exchange="NYSE", type="Stock"),
                ]
            ),
        )
        assert_that(self.ticker_count(), equal_to(2))

    def test_ignore_duplicate_ticker(self):
        self.add_remote_ticker(Ticker(ticker="SPY", exchange="ABC", type="ETF"))
        self.add_local_ticker(Ticker(ticker="SPY", exchange="ABC", type="ETF"))

        self.whenExecuted()

        assert_that(
            self.local_tickers(),
            equal_to([Ticker(ticker="SPY", exchange="ABC", type="ETF")]),
        )
        assert_that(self.ticker_count(), equal_to(0))

    def add_remote_ticker(self, ticker: Ticker):
        self.env.remote.tickers.add_ticker(ticker)

    def local_tickers(self):
        return self.env.local.tickers.get_tickers()

    def add_local_ticker(self, ticker: Ticker):
        self.env.local.tickers.add_ticker(ticker)

    def whenExecuted(self):
        cmd = ImportSymbols(self.env.remote.tickers, self.env.local.tickers)
        self.result = cmd.execute(ImportSymbolsRequest(provider="alpaca"))

    def ticker_count(self):
        assert_that(self.result.is_success(), equal_to(True))
        return self.result.result

    def test_unsupported_provider_fails(self):
        cmd = ImportSymbols(self.env.remote.tickers, self.env.local.tickers)
        result = cmd.execute(ImportSymbolsRequest(provider="tiingo"))

        assert_that(result.is_invalid_data(), equal_to(True))
        assert_that(
            result.errors,
            equal_to(["only the 'alpaca' provider is currently supported"]),
        )
