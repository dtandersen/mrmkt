"""SMA indicator command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.sma import sma


@dataclass(frozen=True)
class SmaRequest:
    symbol: str
    period: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class SmaResult(BaseResult[IndicatorSeriesResult]):
    pass


class CalculateSma(IndicatorSeries, Command[SmaRequest, SmaResult]):
    """Simple moving average over stored closes."""

    @staticmethod
    def label(period: int) -> str:
        return f"SMA_{period}D"

    def execute(self, request: SmaRequest) -> SmaResult:
        if request.period < 1:
            return SmaResult.invalid_data(["period must be positive"])
        try:
            outcome = self._run(
                request.symbol,
                request.from_date,
                request.to_date,
                (self.label(request.period),),
                lambda closes: sma(closes, request.period),
                lambda value: (value,),
                request.period - 1,
            )
        except ValueError as error:
            return SmaResult.invalid_data([str(error)])
        except Exception as error:
            return SmaResult.error(
                [f"Failed to calculate {self.label(request.period)}: {error}"]
            )
        return SmaResult.success(outcome)
