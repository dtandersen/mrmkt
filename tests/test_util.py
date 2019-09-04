import datetime
import unittest

from hamcrest import *

from common.util import to_date


class TestFMPFinancialGateway(unittest.TestCase):
    def test_date(self):
        assert_that(to_date('2019-01-01'), equal_to(datetime.date(2019, 1, 1)))

    def test_date2(self):
        assert_that(to_date('2018-05'), equal_to(datetime.date(2018, 5, 1)))
