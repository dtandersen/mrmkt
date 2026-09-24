"""Stored trigger commands (create/list/remove/enable/disable)."""

from collections.abc import Callable

import typer

from mrmkt.command import _shared
from mrmkt.entity.trigger import Trigger

TRIGGER_COLUMNS = [
    "id",
    "name",
    "symbol",
    "signal",
    "operator",
    "value",
    "frequency",
    "expires_at",
    "message",
    "enabled",
]


def _render_triggers_csv(triggers: list[Trigger]) -> str:
    """Deterministic CSV of stored triggers."""
    lines = ["# generator=mrmkt trigger list", ",".join(TRIGGER_COLUMNS)]
    for trigger in sorted(triggers, key=lambda t: t.id or 0):
        lines.append(
            ",".join(
                [
                    str(trigger.id),
                    trigger.name,
                    trigger.symbol,
                    trigger.signal,
                    trigger.operator,
                    repr(trigger.value) if trigger.value is not None else "",
                    trigger.frequency,
                    trigger.expires_at.isoformat() if trigger.expires_at else "",
                    trigger.message.replace(",", ";"),
                    "true" if trigger.enabled else "false",
                ]
            )
        )
    return "\n".join(lines) + "\n"


def _default_trigger_name() -> str:
    import secrets

    return f"trigger-{secrets.randbelow(900000) + 100000}"


def _set_trigger_enabled(trigger_id: int, enabled: bool) -> None:
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        updated = repository.set_trigger_enabled(trigger_id, enabled)
    except Exception as error:
        typer.echo(f"Failed to update trigger: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    if not updated:
        raise typer.BadParameter(f"no trigger with id {trigger_id}")
    typer.echo(f"trigger {trigger_id} {'enabled' if enabled else 'disabled'}")
