"""Triggerset CLI commands (thin wrappers around trigger-set commands)."""

import typer

from mrmkt.command.add_triggerset import AddTriggerToSetError
from mrmkt.composition import AppContext, resolve_cli_dependencies

triggerset_app = typer.Typer(no_args_is_help=True, help="Manage trigger sets")


@triggerset_app.command("create")
def triggerset_create(
    ctx: typer.Context,
    name: str | None = typer.Argument(
        None, help="Set name (default: triggerset-######)"
    ),
) -> None:
    """Create an empty trigger set; prints its name."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        create_command = env.command_factory.create_trigger_set()
        stored = create_command.execute(name=name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to create trigger set: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"created trigger set {stored}")


@triggerset_app.command("add")
def triggerset_add(
    ctx: typer.Context,
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to add"),
) -> None:
    """Add a trigger to a trigger set."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        add_command = env.command_factory.add_trigger_to_set()
        add_command.execute(set_name=set_name, trigger_name=trigger_name)
    except AddTriggerToSetError as error:
        for field_error in error.errors:
            typer.echo(field_error.message, err=True)
        raise typer.Exit(code=1) from error
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to add trigger to set: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"added trigger {trigger_name} to trigger set {set_name}")


@triggerset_app.command("remove")
def triggerset_remove(
    ctx: typer.Context,
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to remove"),
) -> None:
    """Remove a trigger from a trigger set."""
    env: AppContext = resolve_cli_dependencies(ctx)
    try:
        remove_command = env.command_factory.remove_trigger_from_set()
        remove_command.execute(set_name=set_name, trigger_name=trigger_name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to remove trigger from set: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"removed trigger {trigger_name} from trigger set {set_name}")
