from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import List
from unittest import TestCase

from mrmkt.common.clock import TimeSource
from mrmkt.common.util import to_datetime_utc
from mrmkt.entity.backtest import DataFeed, BacktestDriver
from mrmkt.ext.tdameritrade import Candle
from mrmkt.entity.strategy import Strategy, Trader
from hamcrest import *

from tests.test_wallclock import TimeSourceStub


class MockDataFeed(DataFeed):
    def __init__(self, clock: TimeSource, window: int):
        self.clock = clock
        self.window = window
        self.candles = []

    def get_candles(self) -> List[Candle]:
        prices = [c for c in self.candles if c.datetime + timedelta(seconds=self.window) <= self.clock.now()]
        return prices

    def add_candles(self, candles):
        for c in candles:
            self.candles.append(c)


@dataclass
class Order:
    type: str


class DumbStrategy(Strategy):
    def __init__(self, ticker: str, trader: Trader):
        self.times_run = 0
        super().__init__(ticker, trader)

    def trade(self):
        self.times_run = self.times_run + 1
        if self.data[-1] == 2:
            self.trader.buy()
        elif self.data[-1] == 3:
            self.trader.sell()


class MockTrader(Trader):
    def __init__(self):
        self.orders = []

    def buy(self):
        self.orders.append(Order(type="buy"))

    def sell(self):
        self.orders.append(Order(type="sell"))

    def ema15min8(self):
        pass


class TestBacktestDriver(TestCase):
    def setUp(self) -> None:
        pass

    def test_get_prices(self):
        clock = TimeSourceStub()
        trader = MockTrader()
        strategy = DumbStrategy("SPY", trader)
        prices = MockDataFeed(clock, 15 * 60)
        # prices.add([
        #     1, 2, 3
        # ])
        prices.add_candles([
            Candle(
                datetime=to_datetime_utc("2019-12-12 08:30:00"),
                close=1
            ),
            Candle(
                datetime=to_datetime_utc("2019-12-12 08:45:00"),
                close=2
            ),
            Candle(
                datetime=to_datetime_utc("2019-12-12 09:00:00"),
                close=3
            )
        ])
        driver = BacktestDriver(prices, strategy, clock)
        clock.set_time(to_datetime_utc("2019-12-12 08:45:00"))
        driver.go()

        assert_that(trader.orders, empty())
        assert_that(strategy.data, equal_to([1]))

        clock.set_time(to_datetime_utc("2019-12-12 09:00:00"))
        driver.go()
        assert_that(trader.orders, equal_to([Order(type="buy")]))
        assert_that(strategy.data, equal_to([1, 2]))

        clock.set_time(to_datetime_utc("2019-12-12 09:15:00"))
        driver.go()
        assert_that(trader.orders, equal_to([Order(type="buy"), Order(type="sell")]))
        assert_that(strategy.data, equal_to([1, 2, 3]))

        driver.go()

    def test_wait_for_new_data(self):
        clock = TimeSourceStub()
        trader = MockTrader()
        strategy = DumbStrategy("SPY", trader)
        prices = MockDataFeed(clock, 15 * 60)
        driver = BacktestDriver(prices, strategy, clock)
        clock.set_time(to_datetime_utc("2019-12-12 08:45:00"))
        driver.go()

        assert_that(strategy.data, equal_to([]))
        assert_that(trader.orders, empty())
        assert_that(strategy.times_run, equal_to(0))

        prices.add_candles([
            Candle(
                datetime=to_datetime_utc("2019-12-12 08:30:00"),
                close=1
            )
        ])

        driver.go()
        assert_that(strategy.data, equal_to([1]))

    def test_dont_repeat(self):
        clock = TimeSourceStub()
        trader = MockTrader()
        strategy = DumbStrategy("SPY", trader)
        prices = MockDataFeed(clock, 15 * 60)
        driver = BacktestDriver(prices, strategy, clock)
        clock.set_time(to_datetime_utc("2019-12-12 08:45:00"))
        driver.go()

        assert_that(strategy.data, equal_to([]))
        assert_that(trader.orders, empty())
        assert_that(strategy.times_run, equal_to(0))

        prices.add_candles([
            Candle(
                datetime=to_datetime_utc("2019-12-12 08:30:00"),
                close=1
            )
        ])

        driver.go()
        assert_that(strategy.data, equal_to([1]))
        assert_that(strategy.times_run, equal_to(1))

        driver.go()
        assert_that(strategy.data, equal_to([1]))
        assert_that(strategy.times_run, equal_to(1))
