"""Trigger CLI commands (thin wrappers around trigger commands)."""

import typer

from mrmkt.command.create_trigger import CreateTrigger
from mrmkt.command.delete_trigger import DeleteTrigger
from mrmkt.command.list_trigger import ListTriggers
from mrmkt.command.show_trigger import ShowTrigger
from mrmkt.command.triggers_common import _render_triggers_csv
from mrmkt.composition import resolve_cli_dependencies

trigger_app = typer.Typer(
    no_args_is_help=True, help="Manage stored realtime alert triggers"
)


@trigger_app.command("create")
def trigger_create(
    ctx: typer.Context,
    name: str | None = typer.Argument(
        None, help="Trigger name (default: trigger-xxxxx)"
    ),
    symbol: str = typer.Option(..., "--symbol", help="Symbol to watch"),
    signal: str = typer.Option(
        "risk-range", "--signal", help="Signal source (only 'risk-range')"
    ),
    operator: str = typer.Option(
        "crossing-down",
        "--operator",
        help="Trigger operator (crossing-down, crossing-up, greater-than, less-than)",
    ),
    value: float | None = typer.Option(
        None,
        "--value",
        help="Fixed trigger level (default: computed risk-range buy level)",
    ),
    frequency: str = typer.Option(
        "once_per_rearm",
        "--frequency",
        help="Firing cadence (once_per_rearm, once, every_time)",
    ),
    expires: str | None = typer.Option(
        None, "--expires", help="Expiry date YYYY-MM-DD (default: never)"
    ),
    message: str = typer.Option(
        "",
        "--message",
        help="Message template ({symbol} {price} {level} {moment} {session})",
    ),
) -> None:
    """Store a realtime trigger; prints the created row."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(CreateTrigger) as create_command:
            stored = create_command.execute(
                name,
                symbol,
                signal=signal,
                operator=operator,
                value=value,
                frequency=frequency,
                expires=expires,
                message=message,
            )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to add trigger: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(_render_triggers_csv([stored]), nl=False)


@trigger_app.command("list")
def triggers_list(
    ctx: typer.Context,
    enabled_only: bool = typer.Option(
        False, "--enabled-only", help="List only enabled triggers"
    ),
) -> None:
    """List stored triggers as deterministic CSV."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(ListTriggers) as list_command:
            triggers = list_command.execute(enabled_only=enabled_only)
    except Exception as error:
        typer.echo(f"Failed to list triggers: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(_render_triggers_csv(triggers), nl=False)


@trigger_app.command("show")
def trigger_show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Trigger name from trigger list"),
) -> None:
    """Show a single stored trigger as CSV."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(ShowTrigger) as show_command:
            trigger = show_command.execute(name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to show trigger: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(_render_triggers_csv([trigger]), nl=False)


@trigger_app.command("delete")
def triggers_delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Trigger name from trigger list"),
) -> None:
    """Delete a stored trigger (also removed from any trigger sets)."""
    deps = resolve_cli_dependencies(ctx)
    try:
        with deps.command_factory(DeleteTrigger) as delete_command:
            trigger = delete_command.execute(name)
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to remove trigger: {error}", err=True)
        raise typer.Exit(code=1) from error
    typer.echo(f"deleted trigger {trigger.name}")
