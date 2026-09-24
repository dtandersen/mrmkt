"""Stored trigger create command."""

from datetime import date

import typer

from mrmkt.command._shared import _resolve_signal, normalize_symbol
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.entity.trigger import Trigger


class CreateTrigger:
    """Store a realtime trigger; raises ValueError on bad input."""

    def __init__(self, repository, name_generator=_default_trigger_name):
        self.repository = repository
        self.name_generator = name_generator

    def execute(
        self,
        name: str | None,
        symbol: str,
        signal: str = "risk-range",
        operator: str = "crossing-down",
        value: float | None = None,
        frequency: str = "once_per_rearm",
        expires: str | None = None,
        message: str = "",
    ) -> Trigger:
        try:
            _resolve_signal(signal)
            normalized_symbol = normalize_symbol(symbol)
        except typer.BadParameter as error:
            raise ValueError(str(error)) from error
        trigger_name = name.strip() if name and name.strip() else self.name_generator()
        expires_at = None
        if expires is not None:
            try:
                expires_at = date.fromisoformat(expires)
            except ValueError as error:
                raise ValueError("--expires must be YYYY-MM-DD") from error
        return self.repository.add_trigger(
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
