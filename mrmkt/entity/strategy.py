import copy
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import List

from mrmkt.entity.broker import Broker, Order, OrderListener
from mrmkt.ext.tdameritrade import Candle


@dataclass
class Position:
    quantity: int


class Strategy(OrderListener, metaclass=ABCMeta):
    def __init__(self, ticker: str, broker: Broker):
        self.candles: List[Candle] = []
        self.ticker = ticker
        self.broker = broker
        self.data: List[float] = []
        self.cash = 0
        self.positions = dict()
        self.order_notifications: List[Order] = []

    @abstractmethod
    def trade(self):
        pass


class DumbStrategy(Strategy):
    def __init__(self, ticker: str, broker: Broker):
        self.times_run = 0
        self.shares = 0
        super().__init__(ticker, broker)

    def trade(self):
        self.times_run = self.times_run + 1
        if self.data[-1] == 2:
            quantity = int(self.cash / self.data[-1])
            self.shares = quantity
            self.broker.buy(quantity=quantity, symbol=self.ticker)
        elif self.data[-1] == 3:
            self.broker.sell(quantity=self.shares, symbol=self.ticker)

    def on_order(self, order: Order):
        self.order_notifications.append(copy.copy(order))
