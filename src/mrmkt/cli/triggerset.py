"""Triggerset CLI commands (thin wrappers around trigger-set commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.add_triggerset import AddTriggerToSetRequest
from mrmkt.command.create_triggerset import CreateTriggerSetRequest
from mrmkt.command.remove_triggerset import RemoveTriggerFromSetRequest
from mrmkt.composition import resolve_cli_dependencies

triggerset_app = typer.Typer(no_args_is_help=True, help="Manage trigger sets")


@triggerset_app.command("create")
def triggerset_create(
    ctx: typer.Context,
    name: str | None = typer.Argument(
        None, help="Set name (default: triggerset-######)"
    ),
) -> None:
    """Create an empty trigger set; prints its name."""
    handle(
        ctx,
        lambda factory: factory.create_trigger_set().execute(
            CreateTriggerSetRequest(name=name)
        ),
        lambda stored: typer.echo(f"created trigger set {stored}"),
    )


@triggerset_app.command("add")
def triggerset_add(
    ctx: typer.Context,
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to add"),
) -> None:
    """Add a trigger to a trigger set."""
    env = resolve_cli_dependencies(ctx)
    result = env.command_factory.add_trigger_to_set().execute(
        AddTriggerToSetRequest(set_name=set_name, trigger_name=trigger_name)
    )
    if result.is_success():
        typer.echo(f"added trigger {trigger_name} to trigger set {set_name}")
        return
    for field_error in result.field_errors:
        typer.echo(field_error.message, err=True)
    raise typer.Exit(code=1)


@triggerset_app.command("remove")
def triggerset_remove(
    ctx: typer.Context,
    set_name: str = typer.Argument(..., help="Trigger set name"),
    trigger_name: str = typer.Argument(..., help="Trigger name to remove"),
) -> None:
    """Remove a trigger from a trigger set."""
    handle(
        ctx,
        lambda factory: factory.remove_trigger_from_set().execute(
            RemoveTriggerFromSetRequest(set_name=set_name, trigger_name=trigger_name)
        ),
        lambda _: typer.echo(
            f"removed trigger {trigger_name} from trigger set {set_name}"
        ),
    )
