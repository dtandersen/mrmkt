"""Vol-of-vol indicator command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility_of_volatility


@dataclass(frozen=True)
class VolOfVolRequest:
    symbol: str
    volatility_period: int
    vol_of_vol_period: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class VolOfVolResult(BaseResult[IndicatorSeriesResult]):
    pass


class CalculateVolOfVol(IndicatorSeries, Command[VolOfVolRequest, VolOfVolResult]):
    """Volatility of volatility over stored closes."""

    @staticmethod
    def label(volatility_period: int, vol_of_vol_period: int) -> str:
        return f"VOV_{volatility_period}D_{vol_of_vol_period}D"

    def execute(self, request: VolOfVolRequest) -> VolOfVolResult:
        if request.volatility_period < 2 or request.vol_of_vol_period < 2:
            return VolOfVolResult.invalid_data(
                ["both volatility periods must be at least 2"]
            )
        try:
            outcome = self._run(
                request.symbol,
                request.from_date,
                request.to_date,
                (self.label(request.volatility_period, request.vol_of_vol_period),),
                lambda closes: volatility_of_volatility(
                    closes,
                    request.volatility_period,
                    request.vol_of_vol_period,
                ),
                lambda value: (value,),
                request.volatility_period + request.vol_of_vol_period,
            )
        except ValueError as error:
            return VolOfVolResult.invalid_data([str(error)])
        except Exception as error:
            return VolOfVolResult.error(
                [
                    f"Failed to calculate "
                    f"{self.label(request.volatility_period, request.vol_of_vol_period)}"
                    f": {error}"
                ]
            )
        return VolOfVolResult.success(outcome)
