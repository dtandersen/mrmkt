from abc import ABCMeta, abstractmethod


class Trader(metaclass=ABCMeta):
    @abstractmethod
    def ema15min8(self):
        pass


class Strategy(metaclass=ABCMeta):
    def __init__(self, ticker: str, trader: Trader):
        self.ticker = ticker
        self.trader = trader

    @abstractmethod
    def trade(self):
        pass
