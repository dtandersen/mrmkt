"""Stored trigger commands (create/list/remove/enable/disable)."""


import typer

from mrmkt.command import trigger_app
from mrmkt.command.triggers_common import _set_trigger_enabled


@trigger_app.command("enable")
def triggers_enable(
    trigger_id: int = typer.Argument(..., help="Trigger id from trigger list"),
) -> None:
    """Enable a stored trigger."""
    _set_trigger_enabled(trigger_id, True)
