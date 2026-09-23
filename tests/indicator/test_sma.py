import unittest

from hamcrest import assert_that, equal_to

from mrmkt.indicator.sma import SimpleMovingAverageIndicator, sma


class TestMovingAverage(unittest.TestCase):
    def test_short_series(self):
        series = [3, 2, 1]
        sma = SimpleMovingAverageIndicator().go(series, 2)
        assert_that(sma, equal_to([2.5, 1.5]))

    def test_long_series(self):
        series = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        sma = SimpleMovingAverageIndicator().go(series, 5)
        assert_that(sma, equal_to([3.0, 4.0, 5.0, 6.0, 7.0, 8.0]))

    def test_empty(self):
        sma = SimpleMovingAverageIndicator().go([], 2)
        assert_that(sma, equal_to([]))

    def test_too_short(self):
        sma = SimpleMovingAverageIndicator().go([1, 2, 3], 4)
        assert_that(sma, equal_to([]))

    def test_export(self):
        smax = sma([1, 2, 3], 4)
        assert_that(smax, equal_to([]))

    def test_period_one_returns_original_series(self):
        assert_that(sma([1, 2, 3], 1), equal_to([1.0, 2.0, 3.0]))

    def test_zero_period_is_rejected(self):
        with self.assertRaises(ValueError):
            sma([1, 2, 3], 0)
