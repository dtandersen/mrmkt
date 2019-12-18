from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import List

from backtrader import Order

from mrmkt.ext.tdameritrade import Candle


class OrderListener(metaclass=ABCMeta):
    @abstractmethod
    def on_order(self, order: Order):
        pass


class Broker(metaclass=ABCMeta):
    @abstractmethod
    def ema15min8(self):
        pass

    @abstractmethod
    def buy(self, quantity: int = 0, symbol: str = None):
        pass

    @abstractmethod
    def sell(self, quantity: int = 0, symbol: str = None):
        pass

    @abstractmethod
    def process(self, candle: Candle):
        pass

    @abstractmethod
    def add_listener(self, listener: OrderListener):
        pass


class MockBroker(Broker):
    def __init__(self):
        self.orders = []
        self.listeners: List[OrderListener] = []

    def buy(self, quantity: int = 0, symbol: str = None):
        order = Order(type="buy", quantity=quantity, symbol=symbol, status="PENDING")
        self.orders.append(order)

        for listener in self.listeners:
            listener.on_order(order)

    def sell(self, quantity: int = 0, symbol: str = None):
        self.orders.append(Order(type="sell", quantity=quantity, symbol=symbol, status="PENDING"))

    def process(self, candle: Candle):
        for order in self.orders:
            if order.status == "PENDING":
                order.status = "FULFILLED"

            for listener in self.listeners:
                listener.on_order(order)


    def ema15min8(self):
        pass

    def add_listener(self, listener: OrderListener):
        self.listeners.append(listener)


@dataclass
class Order:
    type: str
    quantity: int
    symbol: str
    status: str
