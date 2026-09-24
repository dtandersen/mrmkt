"""Deterministic risk-range bands from stored bars."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared
from mrmkt.command._shared import normalize_symbol, normalize_tag
from mrmkt.command.alerts import LevelsUseCase, render_levels_csv


def run(
    symbols: list[str] | None = None,
    tags: list[str] | None = None,
    as_of: str | None = None,
    horizon: int = 15,
    vol_period: int = 21,
    width: float = 0.5,
    anchor_period: int = 5,
) -> None:
    """Print deterministic risk-range buy/sell levels from stored bars."""
    if not symbols and not tags:
        raise typer.BadParameter("provide symbols or --tag")
    today = _shared.create_clock().today()
    try:
        as_of_date = _shared.parse_cli_date(as_of, today) if as_of is not None else None
    except ValueError as error:
        raise typer.BadParameter("dates must be ISO dates, now, or durations such as 180d") from error
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        result = LevelsUseCase(repository).execute(
            include_tags=[normalize_tag(tag) for tag in (tags or [])],
            symbols=[normalize_symbol(symbol) for symbol in (symbols or [])],
            as_of=as_of_date,
            horizon=horizon,
            vol_period=vol_period,
            width=width,
            anchor_period=anchor_period,
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to compute levels: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(render_levels_csv(result), nl=False)
