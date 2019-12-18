from abc import ABCMeta, abstractmethod
from dataclasses import dataclass


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


class MockBroker(Broker):
    def __init__(self):
        self.orders = []

    def buy(self, quantity: int = 0, symbol: str = None):
        self.orders.append(Order(type="buy", quantity=quantity, symbol=symbol, status="PENDING"))

    def sell(self, quantity: int = 0, symbol: str = None):
        self.orders.append(Order(type="sell", quantity=quantity, symbol=symbol, status="PENDING"))

    def ema15min8(self):
        pass


@dataclass
class Order:
    type: str
    quantity: int
    symbol: str
    status: str
