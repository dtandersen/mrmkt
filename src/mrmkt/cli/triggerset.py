"""Triggerset CLI commands (thin wrappers around trigger-set commands)."""

from collections.abc import Callable

import typer

from mrmkt.command.add_triggerset import AddTriggerToSet, UnknownTriggerSetError
from mrmkt.command.create_triggerset import CreateTriggerSet
from mrmkt.command.remove_triggerset import RemoveTriggerFromSet
from mrmkt.composition import resolve_trigger_dependencies

triggerset_app = typer.Typer(no_args_is_help=True, help="Manage trigger sets")


@triggerset_app.command("create")
def triggerset_create(
    ctx: typer.Context,
    name: str | None = typer.Argument(
        None, help="Set name (default: triggerset-######)"
    ),
) -> None:
    """Create an empty trigger set; prints its name."""
    deps = resolve_trigger_dependencies(ctx)
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = deps.repository_factory()
        creator = CreateTriggerSet(
            repository, name_generator=deps.triggerset_name_generator
        )
        stored = creator.execute(name)
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
    ctx: typer.Context,
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to add"),
) -> None:
    """Add a trigger to a trigger set."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = resolve_trigger_dependencies(
            ctx
        ).repository_factory()
        AddTriggerToSet(repository).execute(set_name, trigger_name)
    except UnknownTriggerSetError as error:
        typer.echo(f"Triggerset {error.name!r} not found", err=True)
        raise typer.Exit(code=1) from error
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
    ctx: typer.Context,
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to remove"),
) -> None:
    """Remove a trigger from a trigger set."""
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = resolve_trigger_dependencies(
            ctx
        ).repository_factory()
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
