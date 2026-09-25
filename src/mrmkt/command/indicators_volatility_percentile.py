"""Volatility-percentile indicator command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility_percentile


@dataclass(frozen=True)
class VolatilityPercentileRequest:
    symbol: str
    period: int
    lookback: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class VolatilityPercentileResult(BaseResult[IndicatorSeriesResult]):
    pass


class CalculateVolatilityPercentile(
    IndicatorSeries, Command[VolatilityPercentileRequest, VolatilityPercentileResult]
):
    """Volatility percentile rank over stored closes."""

    @staticmethod
    def label(period: int, lookback: int) -> str:
        return f"VOL_{period}D_PCTL_{lookback}D"

    def execute(
        self, request: VolatilityPercentileRequest
    ) -> VolatilityPercentileResult:
        if request.period < 2 or request.lookback < 1:
            return VolatilityPercentileResult.invalid_data(
                ["period must be at least 2 and lookback must be positive"]
            )
        try:
            outcome = self._run(
                request.symbol,
                request.from_date,
                request.to_date,
                (self.label(request.period, request.lookback),),
                lambda closes: volatility_percentile(
                    closes, request.period, request.lookback
                ),
                lambda value: (value,),
                request.period + request.lookback,
            )
        except ValueError as error:
            return VolatilityPercentileResult.invalid_data([str(error)])
        except Exception as error:
            return VolatilityPercentileResult.error(
                [
                    f"Failed to calculate "
                    f"{self.label(request.period, request.lookback)}"
                    f": {error}"
                ]
            )
        return VolatilityPercentileResult.success(outcome)
