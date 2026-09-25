"""Vol-of-vol indicator command."""

from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility_of_volatility


class CalculateVolOfVol(IndicatorSeries):
    """Volatility of volatility over stored closes."""

    @staticmethod
    def label(volatility_period: int, vol_of_vol_period: int) -> str:
        return f"VOV_{volatility_period}D_{vol_of_vol_period}D"

    def execute(
        self,
        symbol: str,
        volatility_period: int,
        vol_of_vol_period: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> IndicatorSeriesResult:
        if volatility_period < 2 or vol_of_vol_period < 2:
            raise ValueError("both volatility periods must be at least 2")
        return self._run(
            symbol,
            from_date,
            to_date,
            (self.label(volatility_period, vol_of_vol_period),),
            lambda closes: volatility_of_volatility(
                closes,
                volatility_period,
                vol_of_vol_period,
            ),
            lambda value: (value,),
            volatility_period + vol_of_vol_period,
        )
