"""Price commands (import/list/freshness)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared, prices_app
from mrmkt.command._shared import normalize_tag
from mrmkt.usecase.freshness import (
    FreshnessRequest,
    FreshnessUseCase,
)
from mrmkt.usecase.freshness import (
    render_csv as render_freshness_csv,
)


@prices_app.command("freshness")
def run_prices_freshness(
    tags: list[str] | None = typer.Option(None, "--tag", help="Include symbols with this tag (repeatable; default: all symbols)"),
    exclude_tags: list[str] | None = typer.Option(None, "--exclude-tag", help="Exclude symbols with this tag (repeatable)"),
    lookback_days: int = typer.Option(365, "--lookback-days", help="Bar-quality window in days"),
    stale_after_days: int = typer.Option(5, "--stale-after", help="Flag symbols with no bar for longer than this"),
    gap_threshold: float = typer.Option(0.20, "--gap-threshold", help="Overnight-gap heuristic threshold as a fraction"),
) -> None:
    """Report price staleness and bar-quality flags; prints deterministic CSV."""
    if lookback_days < 1:
        raise typer.BadParameter("--lookback-days must be at least 1")
    if stale_after_days < 0:
        raise typer.BadParameter("--stale-after must be >= 0")
    if gap_threshold <= 0:
        raise typer.BadParameter("--gap-threshold must be positive")
    today = _shared.create_clock().today()
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        result = FreshnessUseCase(repository).execute(
            FreshnessRequest(
                include_tags=[normalize_tag(tag) for tag in (tags or [])],
                exclude_tags=[normalize_tag(tag) for tag in (exclude_tags or [])],
                today=today,
                lookback_days=lookback_days,
                stale_after_days=stale_after_days,
                gap_threshold=gap_threshold,
            )
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to check freshness: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(render_freshness_csv(result), nl=False)
