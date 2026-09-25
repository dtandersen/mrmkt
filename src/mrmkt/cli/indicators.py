"""Indicator CLI commands (thin wrappers around indicator-series commands)."""

import typer

from mrmkt.command.indicator_series import IndicatorSeriesResult
from mrmkt.command.indicators_risk_range import CalculateRiskRange
from mrmkt.command.indicators_sma import CalculateSma
from mrmkt.command.indicators_vol_of_vol import CalculateVolOfVol
from mrmkt.command.indicators_vol_of_vol_percentile import (
    CalculateVolOfVolPercentile,
)
from mrmkt.command.indicators_volatility import CalculateVolatility
from mrmkt.command.indicators_volatility_percentile import (
    CalculateVolatilityPercentile,
)
from mrmkt.composition import AppContext, resolve_cli_dependencies

indicators_app = typer.Typer(no_args_is_help=True, help="Calculate indicators over stored prices")


@indicators_app.command("sma")
def calculate_sma(
    ctx: typer.Context,
    symbol: str,
    period: int = typer.Option(..., min=1, help="Number of daily bars"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    """Print the simple moving average over stored closes."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        sma_command = env.command_factory.calculate_sma()
        result = sma_command.execute(
            symbol=symbol, period=period, from_date=from_date, to_date=to_date
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(
            f"Failed to calculate {CalculateSma.label(period)}: {error}", err=True
        )
        raise typer.Exit(code=1) from error
    _echo_indicator_series(result)


@indicators_app.command("risk-range")
def calculate_risk_range(
    ctx: typer.Context,
    symbol: str,
    horizon: int = typer.Option(15, min=1, help="Range horizon in trading days (15 = TRADE, 63 = TREND)"),
    volatility_period: int = typer.Option(21, "--vol-period", min=2),
    width: float = typer.Option(0.5, help="Range half-width in vol-scaled units"),
    anchor_period: int = typer.Option(5, "--anchor-period", min=1, help="Trailing mean the range is centered on"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    """Print risk-range buy/sell levels over stored closes."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        range_command = env.command_factory.calculate_risk_range()
        result = range_command.execute(
            symbol=symbol,
            horizon=horizon,
            volatility_period=volatility_period,
            width=width,
            anchor_period=anchor_period,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        low_name, high_name = CalculateRiskRange.label(horizon)
        typer.echo(
            f"Failed to calculate {low_name}/{high_name}: {error}", err=True
        )
        raise typer.Exit(code=1) from error
    _echo_indicator_series(result)


@indicators_app.command("volatility")
def calculate_volatility(
    ctx: typer.Context,
    symbol: str,
    period: int = typer.Option(..., min=2, help="Number of daily returns"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    """Print realized volatility over stored closes."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        volatility_command = env.command_factory.calculate_volatility()
        result = volatility_command.execute(
            symbol=symbol, period=period, from_date=from_date, to_date=to_date
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(
            f"Failed to calculate {CalculateVolatility.label(period)}: {error}",
            err=True,
        )
        raise typer.Exit(code=1) from error
    _echo_indicator_series(result)


@indicators_app.command("volatility-percentile")
def calculate_volatility_percentile(
    ctx: typer.Context,
    symbol: str,
    period: int = typer.Option(..., min=2, help="Rolling return window"),
    lookback: int = typer.Option(252, min=1, help="Prior volatility values used for ranking"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    """Print the volatility percentile rank over stored closes."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        percentile_command = env.command_factory.calculate_volatility_percentile()
        result = percentile_command.execute(
            symbol=symbol,
            period=period,
            lookback=lookback,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(
            f"Failed to calculate {CalculateVolatilityPercentile.label(period, lookback)}: {error}",
            err=True,
        )
        raise typer.Exit(code=1) from error
    _echo_indicator_series(result)


@indicators_app.command("vol-of-vol")
def calculate_volatility_of_volatility(
    ctx: typer.Context,
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    """Print volatility of volatility over stored closes."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        vov_command = env.command_factory.calculate_vol_of_vol()
        result = vov_command.execute(
            symbol=symbol,
            volatility_period=volatility_period,
            vol_of_vol_period=vol_of_vol_period,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(
            f"Failed to calculate {CalculateVolOfVol.label(volatility_period, vol_of_vol_period)}: {error}",
            err=True,
        )
        raise typer.Exit(code=1) from error
    _echo_indicator_series(result)


@indicators_app.command("vol-of-vol-percentile")
def calculate_volatility_of_volatility_percentile(
    ctx: typer.Context,
    symbol: str,
    volatility_period: int = typer.Option(..., "--vol-period", min=2),
    vol_of_vol_period: int = typer.Option(..., "--vov-period", min=2),
    lookback: int = typer.Option(252, min=1, help="Prior vol-of-vol values used for ranking"),
    from_date: str | None = typer.Option(None, "--from", help="Start date or duration such as 180d"),
    to_date: str | None = typer.Option(None, "--to", help="End date; defaults to today"),
) -> None:
    """Print the vol-of-vol percentile rank over stored closes."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        percentile_command = env.command_factory.calculate_vol_of_vol_percentile()
        result = percentile_command.execute(
            symbol=symbol,
            volatility_period=volatility_period,
            vol_of_vol_period=vol_of_vol_period,
            lookback=lookback,
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(
            f"Failed to calculate {CalculateVolOfVolPercentile.label(volatility_period, vol_of_vol_period, lookback)}: {error}",
            err=True,
        )
        raise typer.Exit(code=1) from error
    _echo_indicator_series(result)


def _echo_indicator_series(result: IndicatorSeriesResult) -> None:
    if not result.points:
        typer.echo("No indicator values available.")
        return
    typer.echo("DATE | CLOSE | " + " | ".join(result.columns))
    for point in result.points:
        values = " | ".join(f"{value:g}" for value in point.values)
        typer.echo(f"{point.date.isoformat()} | {point.close:g} | {values}")
