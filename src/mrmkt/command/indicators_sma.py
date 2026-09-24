"""Indicator calculation commands."""


import typer

from mrmkt.command import indicators_app
from mrmkt.command.indicators_common import _run_indicator_series
from mrmkt.indicator.sma import sma


@indicators_app.command("sma")
def calculate_sma(
    symbol: str,
    period: int = typer.Option(..., min=1, help="Number of daily bars"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    if period < 1:
        raise typer.BadParameter("period must be positive")
    _run_indicator_series(
        symbol,
        from_date,
        to_date,
        f"SMA_{period}D",
        lambda prices: sma(prices, period),
        period - 1,
    )
