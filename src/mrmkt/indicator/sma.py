from collections.abc import Sequence


class SimpleMovingAverageIndicator:
    def go(self, series: Sequence[float], period: int):
        if period < 1:
            raise ValueError("period must be positive")

        length = len(series)
        res = []
        for i in range(length - period + 1):
            subset = series[i:i + period]
            avg = sum(subset) / period
            res.append(avg)

        return res


def sma(series: Sequence[float], period: int):
    s = SimpleMovingAverageIndicator()
    return s.go(series, period)
