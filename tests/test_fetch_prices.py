import datetime
import unittest

from hamcrest import *

from mrmkt.common.util import to_date
from mrmkt.entity.stock_price import StockPrice
from mrmkt.usecase.price_loader import PriceLoader, PriceLoaderRequest, PriceLoaderResult
from tests.testenv import TestEnvironment


class TestFetchPricesCommand(unittest.TestCase):
    def setUp(self) -> None:
        self.env = TestEnvironment()

        self.env.remote.add_apple_financials()
        self.env.remote.with_spy()

        self.lookups = []

    def handle_looup(self, ticker: str):
        self.lookups.append(ticker)

    def test_one_ticker_one_price(self):
        self.env.clock.set_time(to_date("2019-10-05"))
        self.whenExecute(tickers='AAPL')

        assert_that(self.env.remote.prices.list_prices('AAPL'), equal_to([
            StockPrice(
                symbol='AAPL',
                date=datetime.date(2014, 6, 13),
                open=84.5035,
                high=84.7235,
                low=83.2937,
                close=83.6603,
                volume=5.452528E7
            )
        ]))

        assert_that(self.lookups, equal_to([{
            "ticker": 'AAPL',
            "start": None,
            "end": to_date("2019-10-05")
        }]))

    def test_multiple_tickers_multiple_prices(self):
        self.env.clock.set_time(to_date("2019-01-02"))
        self.env.remote.add_netflix_financials()

        self.whenExecute(tickers=['AAPL', 'NFLX'])

        assert_that(self.env.local.prices.all_prices(), equal_to([
            StockPrice(
                symbol='AAPL',
                date=datetime.date(2014, 6, 13),
                open=84.5035,
                high=84.7235,
                low=83.2937,
                close=83.6603,
                volume=5.452528E7
            ),
            StockPrice(
                symbol='NFLX',
                date=to_date('2018-12-31'),
                open=260.16,
                high=270.1001,
                low=260.0,
                close=267.66,
                volume=1.350892E7
            ),
            StockPrice(
                symbol='NFLX',
                date=to_date('2019-01-02'),
                open=259.28,
                high=269.7499,
                low=256.58,
                close=267.66,
                volume=1.1679528E7
            )
        ]))

        assert_that(self.lookups, equal_to([
            {
                "ticker": 'AAPL',
                "start": None,
                "end": to_date("2019-01-02")
            },
            {
                "ticker": 'NFLX',
                "start": None,
                "end": to_date("2019-01-02")
            }
        ]))

    def test_read_tickers_until_current_date(self):
        self.env.clock.set_time(to_date("2019-09-19"))
        self.whenExecute(tickers='SPY', start=to_date("2019-09-19"))

        assert_that(self.env.local.prices.list_prices('SPY'), equal_to([
            StockPrice(
                symbol="SPY",
                date=to_date("2019-09-19"),
                open=301.49,
                high=302.34,
                low=301.015,
                close=301.015,
                volume=4.695743E7
            )
            # ,
            # StockPrice(
            #     symbol="SPY",
            #     date=to_date("2019-09-20"),
            #     open=300.31,
            #     high=300.47,
            #     low=298.45,
            #     close=298.67,
            #     volume=4.6894282E7
            # )
        ]))
        assert_that(self.lookups, equal_to([{
            "ticker": 'SPY',
            "start": to_date("2019-09-19"),
            "end": to_date("2019-09-19")
        }
        ]))

    def test_copy_spy_to_end(self):
        self.whenExecute(tickers='SPY', end=to_date("2019-09-16"))

        assert_that(self.env.local.prices.list_prices('SPY'), equal_to([
            StockPrice(
                symbol="SPY",
                date=to_date("2019-09-16"),
                open=299.85,
                high=300.5,
                low=299.78,
                close=300.195,
                volume=4.6779547E7
            )]))

    def test_copy_spy_start_to_end(self):
        self.whenExecute(tickers='SPY', start=to_date("2019-09-17"), end=to_date("2019-09-17"))

        assert_that(self.env.local.prices.list_prices('SPY'), equal_to([
            StockPrice(
                symbol="SPY",
                date=to_date("2019-09-17"),
                open=299.84,
                high=300.965,
                low=299.84,
                close=300.965,
                volume=4.6916222E7
            )
        ]))

    def test_load_prices_after_date(self):
        self.env.local.prices.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-17"),
            open=301.49,
            high=302.34,
            low=301.015,
            close=301.015,
            volume=4.695743E7
        ))
        self.env.local.prices.add_price(StockPrice(
            symbol="SPY",
            date=to_date("2019-09-19"),
            open=301.49,
            high=302.34,
            low=301.015,
            close=301.015,
            volume=4.695743E7
        ))

        self.whenExecute()

        assert_that(self.env.local.prices.list_prices('AAPL'), equal_to([
            StockPrice(
                symbol='AAPL',
                date=datetime.date(2014, 6, 13),
                open=84.5035,
                high=84.7235,
                low=83.2937,
                close=83.6603,
                volume=5.452528E7
            )
        ]))

        assert_that(self.env.local.prices.list_prices('SPY'), equal_to([
            StockPrice(
                symbol="SPY",
                date=to_date("2019-09-17"),
                open=301.49,
                high=302.34,
                low=301.015,
                close=301.015,
                volume=4.695743E7
            ),
            StockPrice(
                symbol="SPY",
                date=to_date("2019-09-19"),
                open=301.49,
                high=302.34,
                low=301.015,
                close=301.015,
                volume=4.695743E7
            ),
            StockPrice(
                symbol="SPY",
                date=to_date("2019-09-20"),
                open=300.31,
                high=300.47,
                low=298.45,
                close=298.67,
                volume=4.6894282E7
            )
        ]))

    def whenExecute(self, tickers=None, start=None, end=None):
        pl = PriceLoader(self.env.remote, self.env.local, self.env.clock)
        pl.execute(PriceLoaderRequest(tickers=tickers, start=start, end=end),
                   PriceLoaderResult(lookup=self.handle_looup))
