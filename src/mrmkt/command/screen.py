"""Tag-universe technical screen."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared
from mrmkt.command._shared import normalize_tag
from mrmkt.usecase.screen import (
    ScreenRequest,
    ScreenUseCase,
)
from mrmkt.usecase.screen import (
    render_csv as render_screen_csv,
)


def run(
    tags: list[str] | None = None,
    exclude_tags: list[str] | None = None,
    as_of: str | None = None,
    mode: str = "technical-only",
    min_price: float = 0.0,
    min_dollar_vol: float = 0.0,
    min_bars: int = 0,
    max_stale_days: int | None = None,
    top: int | None = None,
) -> None:
    """Rank a tag universe on point-in-time technicals; prints deterministic CSV."""
    if min_price < 0 or min_dollar_vol < 0 or min_bars < 0:
        raise typer.BadParameter(
            "--min-price, --min-dollar-vol, and --min-bars must be >= 0"
        )
    if top is not None and top < 1:
        raise typer.BadParameter("--top must be at least 1")
    today = _shared.create_clock().today()
    try:
        as_of_date = _shared.parse_cli_date(as_of, today) if as_of is not None else None
    except ValueError as error:
        raise typer.BadParameter(
            "dates must be ISO dates, now, or durations such as 180d"
        ) from error
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        result = ScreenUseCase(repository).execute(
            ScreenRequest(
                include_tags=[normalize_tag(tag) for tag in (tags or [])],
                exclude_tags=[normalize_tag(tag) for tag in (exclude_tags or [])],
                as_of=as_of_date,
                mode=mode,
                min_price=min_price,
                min_dollar_vol=min_dollar_vol,
                min_bars=min_bars,
                max_stale_days=max_stale_days,
                top_n=top,
            )
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to run screen: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(render_screen_csv(result), nl=False)
