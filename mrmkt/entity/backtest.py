from abc import ABCMeta, abstractmethod
from typing import List

from mrmkt.common.clock import TimeSource
from mrmkt.entity.strategy import Strategy
from mrmkt.ext.tdameritrade import Candle


class StrategyDriver(metaclass=ABCMeta):
    pass


class DataFeed(metaclass=ABCMeta):
    @abstractmethod
    def get_candles(self) -> List[Candle]:
        pass


class BacktestDriver(StrategyDriver):
    def __init__(self, feed: DataFeed, strategy: Strategy, clock: TimeSource):
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
