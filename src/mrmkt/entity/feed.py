import csv
from abc import ABCMeta, abstractmethod
from datetime import timedelta

from mrmkt.common.clock import TimeSource
from mrmkt.common.util import to_datetime
from mrmkt.entity.candle import Candle


class EndOfFeed(Exception):
    pass


class Feed(metaclass=ABCMeta):
    @abstractmethod
    def get_candles(self) -> list[Candle]:
        pass

    @abstractmethod
    def next(self) -> Candle | None:
        pass


class MockFeed(Feed):
    def __init__(self, clock: TimeSource, window: int):
        self.clock = clock
        self.window = window
        self.candles = []
        self.index = 0

    def get_candles(self) -> list[Candle]:
        prices = [c for c in self.candles if c.datetime + timedelta(seconds=self.window) <= self.clock.now()]
        return prices

    def add_candles(self, candles):
        for c in candles:
            self.candles.append(c)

    def next(self) -> Candle | None:
        if self.index >= len(self.candles):
            raise EndOfFeed

        candle = self.candles[self.index]
        self.index = self.index + 1
        return candle


class CsvFeed(Feed):
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        candles = []
        with open(self.csv_path) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                candle = Candle(
                    close=float(row[0]),
                    datetime=to_datetime(row[1])
                )
                candles.append(candle)
        self.candles = candles
        self.index = 0

    def get_candles(self) -> list[Candle]:
        try:
            if self.index >= len(self.candles):
                raise EndOfFeed()

            c = self.candles
            z = c[:self.index + 1]

            self.index = self.index + 1
            return z
        except IndexError:
            raise EndOfFeed()

    def next(self) -> Candle | None:
        if self.index >= len(self.candles):
            raise EndOfFeed

        candle = self.candles[self.index]
        self.index = self.index + 1
        return candle
