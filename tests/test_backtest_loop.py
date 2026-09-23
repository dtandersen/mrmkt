from pathlib import Path
from typing import Optional
from unittest import TestCase
from hamcrest import assert_that, equal_to, has_length

from mrmkt.entity.broker import MockBroker, Order, Broker
from mrmkt.entity.feed import Feed, CsvFeed, EndOfFeed
from mrmkt.entity.strategy import Strategy, DumbStrategy, Position

FEEDS = Path(__file__).parent / "backtest"


class BacktestLoop:
    def __init__(self, strategy: Strategy):
        self.strategy = strategy
        self.feed: Optional[Feed] = None
        self.broker: Optional[Broker] = None
        self.cash = 0

    def run(self):
        assert self.feed is not None, "BacktestLoop needs a feed; call add_feed() first"
        assert self.broker is not None, "BacktestLoop needs a broker"
        self.strategy.cash = self.cash
        self.broker.add_listener(self.strategy)
        try:
            while True:
                # candles = self.feed.get_candles()
                candle = self.feed.next()
                assert candle is not None, "feed ended without EndOfFeed"
                self.broker.process(candle)
                self.strategy.candles.append(candle)
                candles = self.strategy.candles
                self.buy_sell()
                self.strategy.candles = candles
                self.strategy.data = [c.close for c in candles if c.close is not None]
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
        feed = CsvFeed(str(FEEDS / 'test1.csv'))
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
        feed = CsvFeed(str(FEEDS / 'test2.csv'))
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
        feed = CsvFeed(str(FEEDS / 'test3.csv'))
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
