"""Indicator calculation commands."""


import typer

from mrmkt.command import indicators_app
from mrmkt.command.indicators_common import _run_indicator_series
from mrmkt.indicator.volatility import (
    volatility_of_volatility_percentile,
)


@indicators_app.command("vol-of-vol-percentile")
def calculate_volatility_of_volatility_percentile(
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    lookback: int = typer.Option(252, min=1, help="Prior vol-of-vol values used for ranking"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if volatility_period < 2 or vol_of_vol_period < 2 or lookback < 1:
        raise typer.BadParameter("volatility periods must be at least 2 and lookback must be positive")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOV_{volatility_period}D_{vol_of_vol_period}D_PCTL_{lookback}D",
        lambda prices: volatility_of_volatility_percentile(
            prices,
            volatility_period,
            vol_of_vol_period,
            lookback,
        ),
        volatility_period + vol_of_vol_period + lookback,
    )
