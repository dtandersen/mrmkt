"""Indicator calculation commands."""


import typer

from mrmkt.command import indicators_app
from mrmkt.command.indicators_common import _run_indicator_series
from mrmkt.indicator.volatility import (
    volatility_of_volatility,
)


@indicators_app.command("vol-of-vol")
def calculate_volatility_of_volatility(
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if volatility_period < 2 or vol_of_vol_period < 2:
        raise typer.BadParameter("both volatility periods must be at least 2")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOV_{volatility_period}D_{vol_of_vol_period}D",
        lambda prices: volatility_of_volatility(
            prices,
            volatility_period,
            vol_of_vol_period,
        ),
        volatility_period + vol_of_vol_period,
    )
