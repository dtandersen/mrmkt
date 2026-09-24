"""Stored trigger commands (create/list/remove/enable/disable)."""

from collections.abc import Callable
from datetime import date

import typer

from mrmkt.command import _shared, trigger_app
from mrmkt.command._shared import _resolve_signal, normalize_symbol
from mrmkt.command.triggers_common import _default_trigger_name, _render_triggers_csv
from mrmkt.entity.trigger import FREQUENCIES, OPERATORS, Trigger


@trigger_app.command("create")
def trigger_create(
    name: str | None = typer.Argument(None, help="Trigger name (default: trigger-######)"),
    symbol: str = typer.Option(..., "--symbol", help="Symbol to watch"),
    signal: str = typer.Option("risk-range", "--signal", help="Signal source (only 'risk-range')"),
    operator: str = typer.Option(
        "crossing-down", "--operator", help=f"Trigger operator (one of {', '.join(OPERATORS)})"
    ),
    value: float | None = typer.Option(
        None, "--value", help="Fixed trigger level (default: computed risk-range buy level)"
    ),
    frequency: str = typer.Option(
        "once_per_rearm", "--frequency", help=f"Firing cadence (one of {', '.join(FREQUENCIES)})"
    ),
    expires: str | None = typer.Option(None, "--expires", help="Expiry date YYYY-MM-DD (default: never)"),
    message: str = typer.Option("", "--message", help="Message template ({symbol} {price} {level} {moment} {session})"),
) -> None:
    """Store a realtime trigger; prints the created row."""
    _resolve_signal(signal)
    trigger_name = name.strip() if name and name.strip() else _default_trigger_name()
    normalized_symbol = normalize_symbol(symbol)
    expires_at = None
    if expires is not None:
        try:
            expires_at = date.fromisoformat(expires)
        except ValueError as error:
            raise typer.BadParameter("--expires must be YYYY-MM-DD") from error
    close_repository: Callable[[], None] | None = None
    try:
        repository, close_repository = _shared.create_local_ticker_repository()
        stored = repository.add_trigger(
            Trigger(
                id=None,
                name=trigger_name,
                symbol=normalized_symbol,
                signal=signal.strip().lower(),
                operator=operator.strip().lower(),
                value=value,
                frequency=frequency.strip().lower(),
                expires_at=expires_at,
                message=message,
                enabled=True,
            )
        )
    except ValueError as error:
        raise typer.BadParameter(str(error)) from error
    except Exception as error:
        typer.echo(f"Failed to add trigger: {error}", err=True)
        raise typer.Exit(code=1) from error
    finally:
        if close_repository is not None:
            close_repository()
    typer.echo(_render_triggers_csv([stored]), nl=False)
