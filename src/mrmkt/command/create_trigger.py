"""Stored trigger create command.

Framework-neutral: no Typer, ``mrmkt.ext``, or ``mrmkt.cli`` imports here.
Validation failures are reported as ``INVALID_DATA`` results; the Typer
CLI boundary maps them to ``typer.BadParameter``.
"""

import re
from dataclasses import dataclass
from datetime import date

from mrmkt.command.base import BaseResult, Command
from mrmkt.command.triggers_common import _default_trigger_name
from mrmkt.entity.trigger import FREQUENCIES, OPERATORS, Trigger

_RISK_RANGE_SIGNAL = "risk-range"

_SYMBOL_PATTERN = re.compile(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*")


def resolve_trigger_signal(signal: str) -> str:
    """Normalize the trigger signal source; raise ValueError if unsupported."""
    normalized = (signal or "").strip().lower()
    if normalized != _RISK_RANGE_SIGNAL:
        raise ValueError(f"unknown signal {signal!r} (only 'risk-range' is supported)")
    return normalized


def normalize_trigger_symbol(symbol: str) -> str:
    """Normalize a stock symbol; raise ValueError if malformed."""
    normalized = symbol.strip().upper()
    if _SYMBOL_PATTERN.fullmatch(normalized) is None:
        raise ValueError(f"invalid stock symbol: {symbol}")
    return normalized


def normalize_trigger_operator(operator: str) -> str:
    """Normalize a trigger operator; raise ValueError if unsupported."""
    normalized = operator.strip().lower()
    if normalized not in OPERATORS:
        raise ValueError(f"{normalized!r} is an invalid operator")
    return normalized


def normalize_trigger_frequency(frequency: str) -> str:
    """Normalize a trigger frequency; raise ValueError if unsupported."""
    normalized = frequency.strip().lower()
    if normalized not in FREQUENCIES:
        raise ValueError(f"{normalized!r} is an invalid frequency")
    return normalized


@dataclass(frozen=True)
class CreateTriggerRequest:
    name: str | None
    symbol: str
    signal: str = "risk-range"
    operator: str = "crossing-down"
    value: float | None = None
    frequency: str = "once_per_rearm"
    expires: str | None = None
    message: str = ""


@dataclass
class CreateTriggerResult(BaseResult[Trigger]):
    pass


class CreateTrigger(Command[CreateTriggerRequest, CreateTriggerResult]):
    """Store a realtime trigger.

    Independent field errors (operator, frequency, signal, symbol, expiry)
    are accumulated and reported together in a single result; the
    repository is only called when every field is valid.
    """

    def __init__(self, repository, name_generator=_default_trigger_name):
        self.repository = repository
        self.name_generator = name_generator

    def execute(self, request: CreateTriggerRequest) -> CreateTriggerResult:
        errors: list[tuple[str, str]] = []
        clean: dict[str, str] = {}

        def _collect(field, func, value):
            try:
                clean[field] = func(value)
            except ValueError as error:
                errors.append((field, str(error)))

        _collect("operator", normalize_trigger_operator, request.operator)
        _collect("frequency", normalize_trigger_frequency, request.frequency)
        _collect("signal", resolve_trigger_signal, request.signal)
        _collect("symbol", normalize_trigger_symbol, request.symbol)

        expires_at = None
        if request.expires is not None:
            try:
                expires_at = date.fromisoformat(request.expires)
            except ValueError:
                errors.append(("expires", "--expires must be YYYY-MM-DD"))

        if errors:
            return CreateTriggerResult.invalid_data(
                ["; ".join(f"{field}: {message}" for field, message in errors)]
            )

        name = request.name
        trigger_name = name.strip() if name and name.strip() else self.name_generator()
        try:
            stored = self.repository.add_trigger(
                Trigger(
                    id=None,
                    name=trigger_name,
                    symbol=clean["symbol"],
                    signal=clean["signal"],
                    operator=clean["operator"],
                    value=request.value,
                    frequency=clean["frequency"],
                    expires_at=expires_at,
                    message=request.message,
                    enabled=True,
                )
            )
        except ValueError as error:
            return CreateTriggerResult.invalid_data([str(error)])
        except Exception as error:
            return CreateTriggerResult.error([f"Failed to add trigger: {error}"])
        return CreateTriggerResult.success(stored)
