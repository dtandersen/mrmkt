"""Stored trigger commands (create/list/remove/enable/disable)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared, trigger_app


@trigger_app.command("remove")
def triggers_remove(
    trigger_id: int = typer.Argument(..., help="Trigger id from trigger list"),
) -> None:
    """Delete a stored trigger."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        removed = repository.remove_trigger(trigger_id)
    except Exception as error:
        typer.echo(f"Failed to remove trigger: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    if not removed:
        raise typer.BadParameter(f"no trigger with id {trigger_id}")
    typer.echo(f"removed trigger {trigger_id}")
