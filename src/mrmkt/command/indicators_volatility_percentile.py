"""Indicator calculation commands."""


import typer

from mrmkt.command import indicators_app
from mrmkt.command.indicators_common import _run_indicator_series
from mrmkt.indicator.volatility import (
    volatility_percentile,
)


@indicators_app.command("volatility-percentile")
def calculate_volatility_percentile(
    symbol: str,
    period: int = typer.Option(..., min=2, help="Rolling return window"),
    lookback: int = typer.Option(252, min=1, help="Prior volatility values used for ranking"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if period < 2 or lookback < 1:
        raise typer.BadParameter("period must be at least 2 and lookback must be positive")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOL_{period}D_PCTL_{lookback}D",
        lambda prices: volatility_percentile(prices, period, lookback),
        period + lookback,
    )
