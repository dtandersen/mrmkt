"""Vol-of-vol-percentile indicator command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility_of_volatility_percentile


@dataclass(frozen=True)
class VolOfVolPercentileRequest:
    symbol: str
    volatility_period: int
    vol_of_vol_period: int
    lookback: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class VolOfVolPercentileResult(BaseResult[IndicatorSeriesResult]):
    pass


class CalculateVolOfVolPercentile(
    IndicatorSeries, Command[VolOfVolPercentileRequest, VolOfVolPercentileResult]
):
    """Vol-of-vol percentile rank over stored closes."""

    @staticmethod
    def label(volatility_period: int, vol_of_vol_period: int, lookback: int) -> str:
        return f"VOV_{volatility_period}D_{vol_of_vol_period}D_PCTL_{lookback}D"

    def execute(self, request: VolOfVolPercentileRequest) -> VolOfVolPercentileResult:
        if (
            request.volatility_period < 2
            or request.vol_of_vol_period < 2
            or request.lookback < 1
        ):
            return VolOfVolPercentileResult.invalid_data(
                ["volatility periods must be at least 2 and lookback must be positive"]
            )
        try:
            outcome = self._run(
                request.symbol,
                request.from_date,
                request.to_date,
                (
                    self.label(
                        request.volatility_period,
                        request.vol_of_vol_period,
                        request.lookback,
                    ),
                ),
                lambda closes: volatility_of_volatility_percentile(
                    closes,
                    request.volatility_period,
                    request.vol_of_vol_period,
                    request.lookback,
                ),
                lambda value: (value,),
                request.volatility_period
                + request.vol_of_vol_period
                + request.lookback,
            )
        except ValueError as error:
            return VolOfVolPercentileResult.invalid_data([str(error)])
        except Exception as error:
            return VolOfVolPercentileResult.error(
                [
                    f"Failed to calculate "
                    f"{self.label(request.volatility_period, request.vol_of_vol_period, request.lookback)}"
                    f": {error}"
                ]
            )
        return VolOfVolPercentileResult.success(outcome)
