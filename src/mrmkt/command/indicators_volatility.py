"""Indicator calculation commands."""


import typer

from mrmkt.command import indicators_app
from mrmkt.command.indicators_common import _run_indicator_series
from mrmkt.indicator.volatility import (
    volatility,
)


@indicators_app.command("volatility")
def calculate_volatility(
    symbol: str,
    period: int = typer.Option(..., min=2, help="Number of daily returns"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if period < 2:
        raise typer.BadParameter("period must be at least 2")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"VOL_{period}D",
        lambda prices: volatility(prices, period),
        period,
    )
