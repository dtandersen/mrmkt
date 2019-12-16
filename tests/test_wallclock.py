import datetime
from unittest import TestCase
from hamcrest import *

from mrmkt.common.clock import WallClock, TimeSource


class TimeSourceStub(TimeSource):
    def __init__(self):
        self.current_time = None

    def now(self) -> datetime:
        return self.current_time

    def set_time(self, time: datetime):
        self.current_time = time


class TestWallClock(TestCase):
    def test_convert_to_date(self):
        ts = TimeSourceStub()
        ts.current_time = datetime.datetime(2017, 11, 28, 23, 55, 59, 342380)
        clock = WallClock(ts)
        assert_that(clock.today(), equal_to(datetime.date(2017, 11, 28)))