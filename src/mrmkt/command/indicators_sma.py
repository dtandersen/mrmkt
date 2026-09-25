"""SMA indicator command."""

from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.sma import sma


class CalculateSma(IndicatorSeries):
    """Simple moving average over stored closes."""

    @staticmethod
    def label(period: int) -> str:
        return f"SMA_{period}D"

    def execute(
        self,
        symbol: str,
        period: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> IndicatorSeriesResult:
        if period < 1:
            raise ValueError("period must be positive")
        return self._run(
            symbol,
            from_date,
            to_date,
            (self.label(period),),
            lambda closes: sma(closes, period),
            lambda value: (value,),
            period - 1,
        )
