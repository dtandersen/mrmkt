import datetime
import unittest
from math import sqrt
from typing import List

import numpy
from hamcrest import *

from mrmkt.common.util import to_date


class SortinoIndicator(object):
    def __init__(self, risk_free_rate: float, minumum_acceptable_return: float):
        self.minumum_acceptable_return = minumum_acceptable_return
        self.risk_free_rate = risk_free_rate

    def go(self, series: List[float]):
        slen = len(series)
        # x= -.0582 - .02
        # x=x*x
        # print(x)
        negative = []
        for x in series:
            delta = x - self.minumum_acceptable_return
            if delta < 0:
                deviationsqrd = delta * delta
                negative.append(deviationsqrd)
            # else:
            #     negative.append(0)
        s = sum(negative)
        # print(s)
        # monthly_downside_deviation = numpy.std(negative)
        monthly_downside_deviation = sqrt(s / (slen-1))
        print("monthly_downside_deviation="+str(monthly_downside_deviation))
        # print(monthly_downside_deviation)
        annual_downside_deviation = monthly_downside_deviation * pow(12, .5)
        print("annual_downside_deviation="+str(annual_downside_deviation))
        annual_return = 1
        for x in series:
            annual_return = annual_return * (1 + x)
        annual_return = annual_return - 1
        print("annual_return="+str(annual_return))
        # ret = sum(series)
        # print(ret)
        ratio = (annual_return - self.risk_free_rate) / annual_downside_deviation

        return ratio


class TestSortinoIndicator(unittest.TestCase):
    def test_x(self):
        """
        https://xplaind.com/262577/sortino-ratio
        """
        goog = [3.32, .77, 9.21, 6.5, -5.82, 2.4, .95, 2.11, 6, .47, 2.45, 11.81]
        goog = list(map(lambda x: x / 100, goog))
        z = SortinoIndicator(.05, .02).go(goog)
        assert_that(z, equal_to(4.9288829456399945))

    def test_y(self):
        """
        https://xplaind.com/262577/sortino-ratio
        """
        apple = [12.89, 4.87, -.01, 6.34, -5.72, 3.27, 10.27, -6.02, 9.68, 1.66, -1.52, 1.79]
        apple = list(map(lambda x: x / 100, apple))
        z = SortinoIndicator(.05, .02).go(apple)
        assert_that(z, equal_to(2.985580528647642))

    # def test_z(self):
    #     """
    #     https://www.daytrading.com/sortino-ratio
    #     """
    #     apple = [10, 4, 15, -5, 20, -2, 8, -6, 13, 23]
    #     apple = list(map(lambda x: x / 100, apple))
    #     z = SortinoIndicator(0, .07).go(apple)
    #     assert_that(z, equal_to(2.985580528647642))

    # def test_z(self):
    #     """
    #     https://www.ig.com/uk/investments/education/2019/05/01/sortino-ratio-explained
    #     """
    #     apple = [-1.96, -3.4, -2.03, 6.84, 2.8, -.23, 1.52, -3.29, 1.19, -4.85, -1.6, -3.49]
    #     apple = list(map(lambda x: x / 100, apple))
    #     z = SortinoIndicator(.5/100, 0).go(apple)
    #     assert_that(z, equal_to(-1.55))
