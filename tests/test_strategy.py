from unittest import TestCase

from mrmkt.common.util import to_datetime_utc
from mrmkt.entity.backtest import BacktestDriver
from mrmkt.ext.tdameritrade import Candle
from mrmkt.entity.strategy import DumbStrategy
from mrmkt.entity.broker import MockBroker, Order
from mrmkt.entity.feed import MockFeed
from hamcrest import *

from tests.test_wallclock import TimeSourceStub


class TestBacktestDriver(TestCase):
    def setUp(self) -> None:
        pass

    def test_get_prices(self):
        clock = TimeSourceStub()
        trader = MockBroker()
        strategy = DumbStrategy("SPY", trader)
        prices = MockFeed(clock, 15 * 60)
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
        trader = MockBroker()
        strategy = DumbStrategy("SPY", trader)
        prices = MockFeed(clock, 15 * 60)
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
        trader = MockBroker()
        strategy = DumbStrategy("SPY", trader)
        prices = MockFeed(clock, 15 * 60)
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
