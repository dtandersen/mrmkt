from abc import ABCMeta, abstractmethod
from dataclasses import dataclass


class Broker(metaclass=ABCMeta):
    @abstractmethod
    def ema15min8(self):
        pass

    @abstractmethod
    def buy(self):
        pass

    @abstractmethod
    def sell(self):
        pass


class MockBroker(Broker):
    def __init__(self):
        self.orders = []

    def buy(self):
        self.orders.append(Order(type="buy"))

    def sell(self):
        self.orders.append(Order(type="sell"))

    def ema15min8(self):
        pass


@dataclass
class Order:
    type: str
