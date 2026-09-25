"""Volatility-percentile indicator command."""

from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility_percentile


class CalculateVolatilityPercentile(IndicatorSeries):
    """Volatility percentile rank over stored closes."""

    @staticmethod
    def label(period: int, lookback: int) -> str:
        return f"VOL_{period}D_PCTL_{lookback}D"

    def execute(
        self,
        symbol: str,
        period: int,
        lookback: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> IndicatorSeriesResult:
        if period < 2 or lookback < 1:
            raise ValueError(
                "period must be at least 2 and lookback must be positive"
            )
        return self._run(
            symbol,
            from_date,
            to_date,
            (self.label(period, lookback),),
            lambda closes: volatility_percentile(closes, period, lookback),
            lambda value: (value,),
            period + lookback,
        )
