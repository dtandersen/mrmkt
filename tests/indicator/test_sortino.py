import datetime
import unittest
from math import sqrt
from typing import List

import numpy
from hamcrest import *

from mrmkt.common.util import to_date


class SortinoIndicator(object):
    def __init__(self, dtr: float):
        """
        :param dtr: desired target return
        """
        self.dtr = dtr
        # self.risk_free_rate = risk_free_rate

    def go(self, series: List[float]):
        slen = len(series)
        # x= -.0582 - .02
        # x=x*x
        # print(x)
        target_downside_deviation = SortinoIndicator.downside_deviation(series, self.dtr)
        # monthly_downside_deviation = sqrt(s / (slen - 1))
        # print(monthly_downside_deviation)
        # annual_downside_deviation = monthly_downside_deviation * pow(12, .5)
        # print("annual_downside_deviation=" + str(annual_downside_deviation))
        average_period_return = sum(series) / len(series)

        print("average_period_return=" + str(average_period_return))
        print("target return=" + str(self.dtr))
        print("target_downside_deviation=" + str(target_downside_deviation))
        # ret = sum(series)
        # print(ret)
        numerator = average_period_return - self.dtr
        print("numerator=" + str(numerator))
        ratio = (numerator) / target_downside_deviation
        print("sortino=" + str(ratio))
        return ratio

    @staticmethod
    def downside_deviation(returns, target_return):
        negative = []
        for data_point in returns:
            delta = data_point - target_return
            # negative.append(min(delta, 0))
            if delta < 0:
                deviationsqrd = delta * delta
                negative.append(deviationsqrd)
                # negative.append(delta)
            else:
                negative.append(0)

        print(negative)
        s = sqrt(sum(negative) / len(returns))
        # print(s)
        # series.add()
        # downside_deviation = numpy.std(negative)
        return s

    # def monthly_return_to_annual_return(self, series):
    #     annual_return = 1
    #     for x in series:
    #         annual_return = annual_return * (1 + x)
    #     # annual_return = annual_return ** (12 / len(series)) - 1
    #     annual_return = annual_return - 1
    #     return annual_return


class TestSortinoIndicator(unittest.TestCase):
    def test_x(self):
        """
        https://www.cmegroup.com/education/files/rr-sortino-a-sharper-ratio.pdf
        """
        returns = [17, 15, 23, -5, 12, 9, 13, -4]
        returns = list(map(lambda x: x / 100, returns))
        z = SortinoIndicator(0).go(returns)
        assert_that(z, equal_to(4.417261042993861))

    def test_y(self):
        """
        https://xplaind.com/262577/sortino-ratio
        """
        apple = [12.89, 4.87, -.01, 6.34, -5.72, 3.27, 10.27, -6.02, 9.68, 1.66, -1.52, 1.79]
        apple = list(map(lambda x: x / 100, apple))
        z = SortinoIndicator(.05 / 12).go(apple)
        assert_that(z, equal_to(1.0296649721448592))

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

    def test_z(self):
        """
        https://www.ig.com/uk/investments/education/2019/05/01/sortino-ratio-explained
        """
        apple = [
            1.91, 7.91, -1.18, 5.89, -1.66, 7.84, 4.30, 6.12, -2.54, 6.04, 3.55, 5.62,
            1.15, 4.03,  0.40, 13.09, -2.15, 8.88, 3.34, 1.36, 5.18, 2.24
        ]
        apple = list(map(lambda x: x / 100, apple))
        z = SortinoIndicator(0).go(apple)
        assert_that(z, equal_to(4.443741058651983))
