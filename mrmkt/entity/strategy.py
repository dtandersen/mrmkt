from abc import ABCMeta, abstractmethod
from typing import List

from mrmkt.entity.broker import Broker
from mrmkt.ext.tdameritrade import Candle


class Strategy(metaclass=ABCMeta):
    def __init__(self, ticker: str, broker: Broker):
        self.candles: List[Candle] = []
        self.ticker = ticker
        self.broker = broker
        self.data = []

    @abstractmethod
    def trade(self):
        pass


class DumbStrategy(Strategy):
    def __init__(self, ticker: str, broker: Broker):
        self.times_run = 0
        super().__init__(ticker, broker)

    def trade(self):
        self.times_run = self.times_run + 1
        if self.data[-1] == 2:
            self.broker.buy()
        elif self.data[-1] == 3:
            self.broker.sell()