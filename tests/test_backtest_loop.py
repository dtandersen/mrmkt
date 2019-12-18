from typing import Optional
from unittest import TestCase
from hamcrest import *

from mrmkt.entity.broker import MockBroker, Order
from mrmkt.entity.feed import Feed, CsvFeed, EndOfFeed
from mrmkt.entity.strategy import Strategy, DumbStrategy


class BacktestLoop:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.feed: Optional[Feed] = None

    def run(self):
        try:
            while True:
                candles = self.feed.get_candles()
                self.strategy.candles = candles
                self.strategy.data = [c.close for c in candles]
                self.strategy.trade()
        except EndOfFeed:
            pass

    def add_feed(self, feed: Feed):
        self.feed = feed


class TestBuffetModel(TestCase):
    def setUp(self):
        pass

    def test_loop(self):
        feed = CsvFeed('backtest/test1.csv')
        broker = MockBroker()
        strategy = DumbStrategy(ticker="X", broker=broker)
        loop = BacktestLoop(strategy=strategy)
        loop.broker = broker
        loop.add_feed(feed)
        loop.run()
        assert_that(strategy.times_run, equal_to(3))
        assert_that(broker.orders, equal_to([Order(type="buy"), Order(type="sell")]))
