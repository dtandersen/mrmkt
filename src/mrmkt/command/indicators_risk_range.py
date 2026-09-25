"""Risk-range indicator command."""

from dataclasses import dataclass

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.risk_range import risk_range_series


@dataclass(frozen=True)
class RiskRangeRequest:
    symbol: str
    horizon: int
    volatility_period: int
    width: float
    anchor_period: int
    from_date: str | None = None
    to_date: str | None = None


@dataclass
class RiskRangeResult(BaseResult[IndicatorSeriesResult]):
    pass


class CalculateRiskRange(IndicatorSeries, Command[RiskRangeRequest, RiskRangeResult]):
    """Risk-range buy/sell levels over stored closes."""

    @staticmethod
    def label(horizon: int) -> tuple[str, str]:
        return (f"RR_{horizon}D_LRR", f"RR_{horizon}D_TRR")

    def execute(self, request: RiskRangeRequest) -> RiskRangeResult:
        if request.width <= 0:
            return RiskRangeResult.invalid_data(["width must be positive"])
        try:
            outcome = self._run(
                request.symbol,
                request.from_date,
                request.to_date,
                self.label(request.horizon),
                lambda closes: risk_range_series(
                    closes,
                    request.horizon,
                    vol_period=request.volatility_period,
                    width=request.width,
                    anchor_period=request.anchor_period,
                ),
                lambda band: (band.low, band.high),
                request.volatility_period,
            )
        except ValueError as error:
            return RiskRangeResult.invalid_data([str(error)])
        except Exception as error:
            low_name, high_name = self.label(request.horizon)
            return RiskRangeResult.error(
                [f"Failed to calculate {low_name}/{high_name}: {error}"]
            )
        return RiskRangeResult.success(outcome)
