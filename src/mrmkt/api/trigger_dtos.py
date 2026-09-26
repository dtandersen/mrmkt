"""Trigger wire shapes: plain JSON-native dataclasses.

Entities never cross the wire. The web layer maps entities to these
DTOs on the way out and the ``ext`` API client maps them back to
entities at the repository boundary. Parsing here is structural only
(dates, numbers); business validation stays in commands and repos.
"""

import dataclasses
from dataclasses import dataclass
from datetime import date

from mrmkt.command.create_trigger import CreateTriggerRequest
from mrmkt.entity.trigger import Trigger


@dataclass
class TriggerDto:
    """One stored trigger as JSON (dates are ISO strings)."""

    id: int | None
    name: str
    symbol: str
    indicator: str
    operator: str
    value: float | None
    frequency: str
    expires_at: str | None
    message: str
    enabled: bool


@dataclass
class CreateTriggerDto:
    """Trigger creation body; mirrors CreateTriggerRequest field names."""

    name: str | None = None
    symbol: str = ""
    indicator: str = ""
    operator: str = "crossing-down"
    value: float | None = None
    frequency: str = "once_per_rearm"
    expires: str | None = None
    message: str = ""


@dataclass
class SetEnabledDto:
    """Enabled-toggle body for PATCH /api/triggers/{id}."""

    enabled: bool = True


def trigger_to_dto(trigger: Trigger) -> TriggerDto:
    """Render an entity as a JSON-native DTO."""
    return TriggerDto(
        id=trigger.id,
        name=trigger.name,
        symbol=trigger.symbol,
        indicator=trigger.indicator,
        operator=trigger.operator,
        value=trigger.value,
        frequency=trigger.frequency,
        expires_at=trigger.expires_at.isoformat() if trigger.expires_at else None,
        message=trigger.message,
        enabled=trigger.enabled,
    )


def trigger_to_json(trigger: Trigger) -> dict:
    """Render an entity as a plain JSON dict."""
    return dataclasses.asdict(trigger_to_dto(trigger))


def _coerce_dto(data: TriggerDto | dict, field: str):
    if isinstance(data, dict):
        return data.get(field)
    return getattr(data, field)


def _required_str(data: TriggerDto | dict, field: str) -> str:
    value = _coerce_dto(data, field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {field!r}")
    return value


def trigger_from_dto(data: TriggerDto | dict) -> Trigger:
    """Parse a DTO (or plain dict) into an entity; structural errors only."""
    try:
        raw_id = _coerce_dto(data, "id")
        expires_raw = _coerce_dto(data, "expires_at")
        expires_at = date.fromisoformat(expires_raw) if expires_raw else None
        value_raw = _coerce_dto(data, "value")
        message_raw = _coerce_dto(data, "message")
        return Trigger(
            id=int(raw_id) if raw_id is not None else None,
            name=_required_str(data, "name"),
            symbol=_required_str(data, "symbol"),
            indicator=_required_str(data, "indicator"),
            operator=_required_str(data, "operator"),
            value=float(value_raw) if value_raw is not None else None,
            frequency=_required_str(data, "frequency"),
            expires_at=expires_at,
            message=message_raw if isinstance(message_raw, str) else "",
            enabled=bool(_coerce_dto(data, "enabled")),
        )
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError(f"malformed trigger DTO: {error}") from error


def create_request_from_dto(data: CreateTriggerDto | dict) -> CreateTriggerRequest:
    """Map a creation body onto the command request (same field names)."""
    if isinstance(data, dict):
        data = CreateTriggerDto(
            name=data.get("name"),
            symbol=data.get("symbol", ""),
            indicator=data.get("indicator", ""),
            operator=data.get("operator", "crossing-down"),
            value=data.get("value"),
            frequency=data.get("frequency", "once_per_rearm"),
            expires=data.get("expires"),
            message=data.get("message", ""),
        )
    return CreateTriggerRequest(
        name=data.name,
        symbol=data.symbol,
        indicator=data.indicator,
        operator=data.operator,
        value=data.value,
        frequency=data.frequency,
        expires=data.expires,
        message=data.message,
    )
