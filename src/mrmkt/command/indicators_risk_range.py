"""Risk-range indicator command."""

from mrmkt.command.indicator_series import IndicatorSeries, IndicatorSeriesResult
from mrmkt.indicator.risk_range import risk_range_series


class CalculateRiskRange(IndicatorSeries):
    """Risk-range buy/sell levels over stored closes."""

    @staticmethod
    def label(horizon: int) -> tuple[str, str]:
        return (f"RR_{horizon}D_LRR", f"RR_{horizon}D_TRR")

    def execute(
        self,
        symbol: str,
        horizon: int,
        volatility_period: int,
        width: float,
        anchor_period: int,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> IndicatorSeriesResult:
        if width <= 0:
            raise ValueError("width must be positive")
        return self._run(
            symbol,
            from_date,
            to_date,
            self.label(horizon),
            lambda closes: risk_range_series(
                closes,
                horizon,
                vol_period=volatility_period,
                width=width,
                anchor_period=anchor_period,
            ),
            lambda band: (band.low, band.high),
            volatility_period,
        )
