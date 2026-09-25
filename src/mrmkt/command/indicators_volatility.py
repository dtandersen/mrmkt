"""Volatility indicator command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.volatility import volatility


@dataclass(frozen=True)
class VolatilityRequest:
    symbol: str
    period: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class VolatilityResult(BaseResult[IndicatorSeriesResult]):
    pass


class CalculateVolatility(
    IndicatorSeries, Command[VolatilityRequest, VolatilityResult]
):
    """Realized volatility over stored closes."""

    @staticmethod
    def label(period: int) -> str:
        return f"VOL_{period}D"

    def execute(self, request: VolatilityRequest) -> VolatilityResult:
        if request.period < 2:
            return VolatilityResult.invalid_data(["period must be at least 2"])
        try:
            outcome = self._run(
                request.symbol,
                request.from_date,
                request.to_date,
                (self.label(request.period),),
                lambda closes: volatility(closes, request.period),
                lambda value: (value,),
                request.period,
            )
        except ValueError as error:
            return VolatilityResult.invalid_data([str(error)])
        except Exception as error:
            return VolatilityResult.error(
                [f"Failed to calculate {self.label(request.period)}: {error}"]
            )
        return VolatilityResult.success(outcome)
