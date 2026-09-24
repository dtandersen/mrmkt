"""Stored trigger commands (create/list/show/remove)."""

from mrmkt.entity.trigger import Trigger

TRIGGER_COLUMNS = [
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
    for trigger in sorted(triggers, key=lambda t: t.name):
        lines.append(
            ",".join(
                [
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

    return f"trigger-{_to_base36(secrets.randbelow(36 ** 5)).rjust(5, _BASE36_ALPHABET[0])}"


_BASE36_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _to_base36(value: int) -> str:
    """Encode a non-negative int as base36 (0-9a-z, case-insensitive safe)."""
    if value < 0:
        raise ValueError("base36 encodes non-negative integers")
    if value == 0:
        return _BASE36_ALPHABET[0]
    digits = []
    while value:
        value, remainder = divmod(value, 36)
        digits.append(_BASE36_ALPHABET[remainder])
    return "".join(reversed(digits))
