"""Trigger CLI commands (thin wrappers around trigger commands)."""

import typer

from mrmkt.cli.results import handle
from mrmkt.command.create_trigger import CreateTriggerRequest
from mrmkt.command.delete_trigger import DeleteTriggerRequest
from mrmkt.command.list_trigger import ListTriggersRequest
from mrmkt.command.show_trigger import ShowTriggerRequest
from mrmkt.command.triggers_common import _render_triggers_csv

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
    handle(
        ctx,
        lambda factory: factory.create_trigger().execute(
            CreateTriggerRequest(
                name=name,
                symbol=symbol,
                signal=signal,
                operator=operator,
                value=value,
                frequency=frequency,
                expires=expires,
                message=message,
            )
        ),
        lambda stored: typer.echo(_render_triggers_csv([stored]), nl=False),
    )


@trigger_app.command("list")
def triggers_list(
    ctx: typer.Context,
    enabled_only: bool = typer.Option(
        False, "--enabled-only", help="List only enabled triggers"
    ),
) -> None:
    """List stored triggers as deterministic CSV."""
    handle(
        ctx,
        lambda factory: factory.list_triggers().execute(
            ListTriggersRequest(enabled_only=enabled_only)
        ),
        lambda triggers: typer.echo(_render_triggers_csv(triggers), nl=False),
    )


@trigger_app.command("show")
def trigger_show(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Trigger name from trigger list"),
) -> None:
    """Show a single stored trigger as CSV."""
    handle(
        ctx,
        lambda factory: factory.show_trigger().execute(ShowTriggerRequest(name=name)),
        lambda trigger: typer.echo(_render_triggers_csv([trigger]), nl=False),
    )


@trigger_app.command("delete")
def triggers_delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Trigger name from trigger list"),
) -> None:
    """Delete a stored trigger (also removed from any trigger sets)."""
    handle(
        ctx,
        lambda factory: factory.delete_trigger().execute(
            DeleteTriggerRequest(name=name)
        ),
        lambda trigger: typer.echo(f"deleted trigger {trigger.name}"),
    )
