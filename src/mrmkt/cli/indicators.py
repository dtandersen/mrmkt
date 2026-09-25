"""Indicator CLI commands (thin wrappers around indicator-series commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.indicator_series import IndicatorSeriesResult
from mrmkt.command.indicators_risk_range import RiskRangeRequest
from mrmkt.command.indicators_sma import SmaRequest
from mrmkt.command.indicators_vol_of_vol import VolOfVolRequest
from mrmkt.command.indicators_vol_of_vol_percentile import (
    VolOfVolPercentileRequest,
)
from mrmkt.command.indicators_volatility import VolatilityRequest
from mrmkt.command.indicators_volatility_percentile import (
    VolatilityPercentileRequest,
)

indicators_app = typer.Typer(
    no_args_is_help=True, help="Calculate indicators over stored prices"
)


@indicators_app.command("sma")
def calculate_sma(
    ctx: typer.Context,
    symbol: str,
    period: int = typer.Option(..., min=1, help="Number of daily bars"),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date or duration such as 180d"
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date; defaults to today"
    ),
) -> None:
    """Print the simple moving average over stored closes."""
    handle(
        ctx,
        lambda factory: factory.calculate_sma().execute(
            SmaRequest(
                symbol=symbol, period=period, from_date=from_date, to_date=to_date
            )
        ),
        _echo_indicator_series,
    )


@indicators_app.command("risk-range")
def calculate_risk_range(
    ctx: typer.Context,
    symbol: str,
    horizon: int = typer.Option(
        15, min=1, help="Range horizon in trading days (15 = TRADE, 63 = TREND)"
    ),
    volatility_period: int = typer.Option(21, "--vol-period", min=2),
    width: float = typer.Option(0.5, help="Range half-width in vol-scaled units"),
    anchor_period: int = typer.Option(
        5, "--anchor-period", min=1, help="Trailing mean the range is centered on"
    ),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date or duration such as 180d"
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date; defaults to today"
    ),
) -> None:
    """Print risk-range buy/sell levels over stored closes."""
    handle(
        ctx,
        lambda factory: factory.calculate_risk_range().execute(
            RiskRangeRequest(
                symbol=symbol,
                horizon=horizon,
                volatility_period=volatility_period,
                width=width,
                anchor_period=anchor_period,
                from_date=from_date,
                to_date=to_date,
            )
        ),
        _echo_indicator_series,
    )


@indicators_app.command("volatility")
def calculate_volatility(
    ctx: typer.Context,
    symbol: str,
    period: int = typer.Option(..., min=2, help="Number of daily returns"),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date or duration such as 180d"
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date; defaults to today"
    ),
) -> None:
    """Print realized volatility over stored closes."""
    handle(
        ctx,
        lambda factory: factory.calculate_volatility().execute(
            VolatilityRequest(
                symbol=symbol, period=period, from_date=from_date, to_date=to_date
            )
        ),
        _echo_indicator_series,
    )


@indicators_app.command("volatility-percentile")
def calculate_volatility_percentile(
    ctx: typer.Context,
    symbol: str,
    period: int = typer.Option(..., min=2, help="Rolling return window"),
    lookback: int = typer.Option(
        252, min=1, help="Prior volatility values used for ranking"
    ),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date or duration such as 180d"
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date; defaults to today"
    ),
) -> None:
    """Print the volatility percentile rank over stored closes."""
    handle(
        ctx,
        lambda factory: factory.calculate_volatility_percentile().execute(
            VolatilityPercentileRequest(
                symbol=symbol,
                period=period,
                lookback=lookback,
                from_date=from_date,
                to_date=to_date,
            )
        ),
        _echo_indicator_series,
    )


@indicators_app.command("vol-of-vol")
def calculate_volatility_of_volatility(
    ctx: typer.Context,
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date or duration such as 180d"
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date; defaults to today"
    ),
) -> None:
    """Print volatility of volatility over stored closes."""
    handle(
        ctx,
        lambda factory: factory.calculate_vol_of_vol().execute(
            VolOfVolRequest(
                symbol=symbol,
                volatility_period=volatility_period,
                vol_of_vol_period=vol_of_vol_period,
                from_date=from_date,
                to_date=to_date,
            )
        ),
        _echo_indicator_series,
    )


@indicators_app.command("vol-of-vol-percentile")
def calculate_volatility_of_volatility_percentile(
    ctx: typer.Context,
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    lookback: int = typer.Option(
        252, min=1, help="Prior vol-of-vol values used for ranking"
    ),
    from_date: str | None = typer.Option(
        None, "--from", help="Start date or duration such as 180d"
    ),
    to_date: str | None = typer.Option(
        None, "--to", help="End date; defaults to today"
    ),
) -> None:
    """Print the vol-of-vol percentile rank over stored closes."""
    handle(
        ctx,
        lambda factory: factory.calculate_vol_of_vol_percentile().execute(
            VolOfVolPercentileRequest(
                symbol=symbol,
                volatility_period=volatility_period,
                vol_of_vol_period=vol_of_vol_period,
                lookback=lookback,
                from_date=from_date,
                to_date=to_date,
            )
        ),
        _echo_indicator_series,
    )


def _echo_indicator_series(result: IndicatorSeriesResult) -> None:
    if not result.points:
        typer.echo("No indicator values available.")
        return
    typer.echo("DATE | CLOSE | " + " | ".join(result.columns))
    for point in result.points:
        values = " | ".join(f"{value:g}" for value in point.values)
        typer.echo(f"{point.date.isoformat()} | {point.close:g} | {values}")
