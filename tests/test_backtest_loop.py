from typing import Optional
from unittest import TestCase
from hamcrest import *

from mrmkt.entity.broker import MockBroker, Order, Broker
from mrmkt.entity.feed import Feed, CsvFeed, EndOfFeed
from mrmkt.entity.strategy import Strategy, DumbStrategy, Position


class BacktestLoop:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.feed: Optional[Feed] = None
        self.broker: Optional[Broker] = None
        self.cash = 0

    def run(self):
        self.strategy.cash = self.cash
        self.broker.add_listener(self.strategy)
        try:
            while True:
                # candles = self.feed.get_candles()
                candle = self.feed.next()
                self.broker.process(candle)
                self.strategy.candles.append(candle)
                candles = self.strategy.candles
                self.buy_sell()
                self.strategy.candles = candles
                self.strategy.data = [c.close for c in candles]
                self.strategy.trade()
        except EndOfFeed:
            pass

    def add_feed(self, feed: Feed):
        self.feed = feed

    def buy_sell(self):
        # for order in self.broker.orders():
        self.strategy.positions["X"] = Position(quantity=100)


class TestBuffetModel(TestCase):
    def setUp(self):
        pass

    def test_buy_and_sell(self):
        feed = CsvFeed('backtest/test1.csv')
        broker = MockBroker()
        strategy = DumbStrategy(ticker="X", broker=broker)
        loop = BacktestLoop(strategy=strategy)
        loop.cash = 100
        loop.broker = broker
        loop.add_feed(feed)
        loop.run()
        assert_that(strategy.times_run, equal_to(3))
        assert_that(broker.orders, equal_to([
            Order(type="buy", quantity=50, symbol="X", status="FULFILLED"),
            Order(type="sell", quantity=50, symbol="X", status="PENDING")
        ]))
        assert_that(strategy.order_notifications, equal_to([
            Order(type='buy', quantity=50, symbol='X', status='PENDING'),
            Order(type='buy', quantity=50, symbol='X', status='FULFILLED')
        ]))

    def test_buy_pending(self):
        feed = CsvFeed('backtest/test2.csv')
        broker = MockBroker()
        strategy = DumbStrategy(ticker="X", broker=broker)
        loop = BacktestLoop(strategy=strategy)
        loop.cash = 200
        loop.broker = broker
        loop.add_feed(feed)
        loop.run()
        assert_that(strategy.times_run, equal_to(2))
        assert_that(broker.orders, has_length(1))
        order = broker.orders[0]
        assert_that(order, equal_to(Order(type="buy", quantity=100, symbol="X", status="PENDING")))
        assert_that(strategy.order_notifications, equal_to([
            Order(type="buy", quantity=100, symbol="X", status="PENDING")
        ]))
        assert_that(strategy.positions["X"].quantity, equal_to(100))

    def test_buy_fulfilled(self):
        feed = CsvFeed('backtest/test3.csv')
        broker = MockBroker()
        strategy = DumbStrategy(ticker="X", broker=broker)
        loop = BacktestLoop(strategy=strategy)
        loop.cash = 200
        loop.broker = broker
        loop.add_feed(feed)
        loop.run()
        assert_that(strategy.times_run, equal_to(3))
        assert_that(broker.orders, has_length(1))
        order = broker.orders[0]
        assert_that(order, equal_to(Order(type="buy", quantity=100, symbol="X", status="FULFILLED")))
        assert_that(strategy.order_notifications, equal_to([
            Order(type="buy", quantity=100, symbol="X", status="PENDING"),
            Order(type="buy", quantity=100, symbol="X", status="FULFILLED")
        ]))
        assert_that(strategy.positions["X"].quantity, equal_to(100))
