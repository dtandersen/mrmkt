"""Triggerset CLI commands (thin wrappers around trigger-set commands)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared
from mrmkt.command.add_triggerset import AddTriggerToSet
from mrmkt.command.create_triggerset import CreateTriggerSet
from mrmkt.command.remove_triggerset import RemoveTriggerFromSet

triggerset_app = typer.Typer(no_args_is_help=True, help="Manage trigger sets")


@triggerset_app.command("create")
def triggerset_create(
    name: str | None = typer.Argument(None, help="Set name (default: triggerset-######)"),
) -> None:
    """Create an empty trigger set; prints its name."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        stored = CreateTriggerSet(repository).execute(name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to create trigger set: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(f"created trigger set {stored}")


@triggerset_app.command("add")
def triggerset_add(
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to add"),
) -> None:
    """Add a trigger to a trigger set."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        AddTriggerToSet(repository).execute(set_name, trigger_name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to add trigger to set: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(f"added trigger {trigger_name} to trigger set {set_name}")


@triggerset_app.command("remove")
def triggerset_remove(
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to remove"),
) -> None:
    """Remove a trigger from a trigger set."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        RemoveTriggerFromSet(repository).execute(set_name, trigger_name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to remove trigger from set: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(f"removed trigger {trigger_name} from trigger set {set_name}")
