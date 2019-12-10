from abc import ABCMeta, abstractmethod


class Trader(metaclass=ABCMeta):
    @abstractmethod
    def ema15min8(self):
        pass

    @abstractmethod
    def buy(self):
        pass

    @abstractmethod
    def sell(self):
        pass


class Strategy(metaclass=ABCMeta):
    def __init__(self, ticker: str, trader: Trader):
        self.ticker = ticker
        self.trader = trader
        self.data = []

    @abstractmethod
    def trade(self):
        pass
