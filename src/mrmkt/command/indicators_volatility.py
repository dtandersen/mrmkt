"""Volatility indicator command."""

from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility


class CalculateVolatility(IndicatorSeries):
    """Realized volatility over stored closes."""

    @staticmethod
    def label(period: int) -> str:
        return f"VOL_{period}D"

    def execute(
        self,
        symbol: str,
        period: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> IndicatorSeriesResult:
        if period < 2:
            raise ValueError("period must be at least 2")
        return self._run(
            symbol,
            from_date,
            to_date,
            (self.label(period),),
            lambda closes: volatility(closes, period),
            lambda value: (value,),
            period,
        )
