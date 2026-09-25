"""Vol-of-vol-percentile indicator command."""

from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility_of_volatility_percentile


class CalculateVolOfVolPercentile(IndicatorSeries):
    """Vol-of-vol percentile rank over stored closes."""

    @staticmethod
    def label(
        volatility_period: int, vol_of_vol_period: int, lookback: int
    ) -> str:
        return f"VOV_{volatility_period}D_{vol_of_vol_period}D_PCTL_{lookback}D"

    def execute(
        self,
        symbol: str,
        volatility_period: int,
        vol_of_vol_period: int,
        lookback: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> IndicatorSeriesResult:
        if volatility_period < 2 or vol_of_vol_period < 2 or lookback < 1:
            raise ValueError(
                "volatility periods must be at least 2 and lookback must be positive"
            )
        return self._run(
            symbol,
            from_date,
            to_date,
            (
                self.label(volatility_period, vol_of_vol_period, lookback),
            ),
            lambda closes: volatility_of_volatility_percentile(
                closes,
                volatility_period,
                vol_of_vol_period,
                lookback,
            ),
            lambda value: (value,),
            volatility_period + vol_of_vol_period + lookback,
        )
