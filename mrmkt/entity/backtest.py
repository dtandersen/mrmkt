from abc import ABCMeta

from mrmkt.common.clock import TimeSource
from mrmkt.entity.feed import Feed
from mrmkt.entity.strategy import Strategy


class StrategyDriver(metaclass=ABCMeta):
    pass


class BacktestDriver(StrategyDriver):
    def __init__(self, feed: Feed, strategy: Strategy, clock: TimeSource):
        self.clock = clock
        self.strategy = strategy
        self.feed = feed

    def go(self):
        candles = self.feed.get_candles()
        if len(candles) == 0:
            return

        if len(self.strategy.candles) > 0:
            last_time = self.strategy.candles[-1].datetime
        else:
            last_time = None

        if last_time is not None and candles[-1].datetime <= last_time:
            return

        self.strategy.candles = candles
        self.strategy.data = [c.close for c in self.strategy.candles]
        self.strategy.trade()
