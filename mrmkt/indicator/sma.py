from typing import List


class SimpleMovingAverageIndicator(object):
    def go(self, series: List[float], period: int):
        length = len(series)
        res = []
        for i in range(0, length - period + 1):
            subset = series[i:i + period]
            avg = sum(subset) / period
            res.append(avg)

        return res


def sma(series: List[float], period: int):
    s = SimpleMovingAverageIndicator()
    return s.go(series, period)
