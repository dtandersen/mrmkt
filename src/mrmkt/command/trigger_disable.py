"""Stored trigger commands (create/list/remove/enable/disable)."""

import typer

from mrmkt.command import trigger_app
from mrmkt.command.triggers_common import _set_trigger_enabled


@trigger_app.command("disable")
def triggers_disable(
    trigger_id: int = typer.Argument(..., help="Trigger id from triggers list"),
) -> None:
    """Disable a stored trigger (it stays in the store)."""
    _set_trigger_enabled(trigger_id, False)
