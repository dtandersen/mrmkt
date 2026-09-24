"""Stored trigger commands (create/list/remove/enable/disable)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared, trigger_app
from mrmkt.command.triggers_common import _render_triggers_csv


@trigger_app.command("list")
def triggers_list(
    enabled_only: bool = typer.Option(False, "--enabled-only", help="List only enabled triggers"),
) -> None:
    """List stored triggers as deterministic CSV."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        triggers = repository.list_triggers(enabled_only=enabled_only)
    except Exception as error:
        typer.echo(f"Failed to list triggers: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(_render_triggers_csv(triggers), nl=False)
