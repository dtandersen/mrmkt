from math import sqrt
from typing import List

import numpy


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
        # avg
        average_period_return = sum(series) / len(series)
        a = numpy.array(series)
        average_period_return= a.prod() ** (1.0 / len(a))

        # print("average_period_return=" + str(average_period_return))
        # print("target return=" + str(self.dtr))
        # print("target_downside_deviation=" + str(target_downside_deviation))
        # ret = sum(series)
        # print(ret)
        numerator = average_period_return - self.dtr
        # print("numerator=" + str(numerator))
        ratio = (numerator) / target_downside_deviation
        # print("sortino=" + str(ratio))
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

        # print(negative)
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