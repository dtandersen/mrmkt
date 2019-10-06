import datetime
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def today(self) -> datetime.date:
        pass


class TimeSource(ABC):
    @abstractmethod
    def now(self) -> datetime.datetime:
        pass


class SystemTimeSource(TimeSource):
    def now(self) -> datetime.datetime:
        return datetime.datetime.now()


class WallClock(Clock):
    def __init__(self, time_source: TimeSource = SystemTimeSource()):
        self.time_source = time_source

    def today(self) -> datetime.date:
        now = self.time_source.now()
        return datetime.date(now.year, now.month, now.day)


class ClockStub(Clock):
    def __init__(self):
        self.time = None

    def set_time(self, time: datetime.date):
        self.time = time

    def today(self) -> datetime.date:
        return self.time
