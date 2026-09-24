"""Indicator calculation commands."""


import typer

from mrmkt.command import indicators_app
from mrmkt.command.indicators_common import _run_indicator_pair_series
from mrmkt.indicator.risk_range import risk_range_series


@indicators_app.command("risk-range")
def calculate_risk_range(
    symbol: str,
    horizon: int = typer.Option(15, min=1, help="Range horizon in trading days (15 = TRADE, 63 = TREND)"),
    volatility_period: int = typer.Option(21, "--vol-period", min=2),
    width: float = typer.Option(0.5, help="Range half-width in vol-scaled units"),
    anchor_period: int = typer.Option(5, "--anchor-period", min=1, help="Trailing mean the range is centered on"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if width <= 0:
        raise typer.BadParameter("width must be positive")
    _run_indicator_pair_series(
        symbol,
        from_date,
        to_date,
        f"RR_{horizon}D_LRR",
        f"RR_{horizon}D_TRR",
        lambda prices: risk_range_series(
            prices,
            horizon,
            vol_period=volatility_period,
            width=width,
            anchor_period=anchor_period,
        ),
        volatility_period,
    )
