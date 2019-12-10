from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from unittest import TestCase

from strategy import Strategy, Trader
from hamcrest import *


class StrategyDriver(metaclass=ABCMeta):
    pass


class PriceGetter(metaclass=ABCMeta):
    @abstractmethod
    def next(self):
        pass


class BacktestDriver(StrategyDriver):
    def __init__(self, prices: PriceGetter, strategy: Strategy):
        self.strategy = strategy
        self.prices = prices

    def go(self):
        try:
            price = self.prices.next()
            self.strategy.data.append(price)
            self.strategy.trade()
        except IndexError:
            pass

class MockPriceGetter(PriceGetter):
    def __init__(self):
        self.prices = []
        self.index = 0

    def add(self, prices):
        self.prices = prices

    def next(self):
        price = self.prices[self.index]
        self.index = self.index + 1
        return price


@dataclass
class Order:
    type: str


class DumbStrategy(Strategy):
    def trade(self):
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
        trader = MockTrader()
        strategy = DumbStrategy("SPY", trader)
        prices = MockPriceGetter()
        prices.add([1, 2, 3])
        driver = BacktestDriver(prices, strategy)
        driver.go()

        assert_that(trader.orders, empty())

        driver.go()
        assert_that(trader.orders, equal_to([Order(type="buy")]))

        driver.go()
        assert_that(trader.orders, equal_to([Order(type="buy"), Order(type="sell")]))


        driver.go()
