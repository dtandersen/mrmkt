import datetime
from abc import ABC, abstractmethod


class Clock(ABC):
    @abstractmethod
    def iso_time(self) -> datetime.date:
        pass


class WallClock(Clock):
    def iso_time(self) -> datetime.date:
        return datetime.datetime.now()


class ClockStub(Clock):
    def __init__(self):
        self.time = None

    def set_time(self, time: datetime.date):
        self.time = time

    def iso_time(self) -> datetime.date:
        return self.time
