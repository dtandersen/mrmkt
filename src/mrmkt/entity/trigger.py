import datetime
import re
from dataclasses import dataclass

INDICATOR_PATTERN = re.compile(r"[a-z0-9][a-z0-9_-]*")


def normalize_trigger_indicator(value: str | None) -> str:
    """Normalize an indicator name; raise ValueError if blank or malformed."""
    normalized = (value or "").strip().lower()
    if not normalized:
        raise ValueError("indicator must not be blank")
    if INDICATOR_PATTERN.fullmatch(normalized) is None:
        raise ValueError(
            f"{normalized!r} is an invalid indicator (use letters, numbers, '-' or '_')"
        )
    return normalized


OPERATORS = (
    "crossing-down",
    "crossing-up",
    "greater-than",
    "less-than",
)

FREQUENCIES = (
    "once_per_rearm",
    "once",
    "every_time",
)

DEFAULT_MESSAGE_TEMPLATE = (
    "{moment} | {session} | {symbol} | {price:g} <= buy {level:g} TRIGGER"
)


@dataclass
class Trigger:
    id: int | None
    name: str
    symbol: str
    indicator: str
    operator: str = "crossing-down"
    value: float | None = None
    frequency: str = "once_per_rearm"
    expires_at: datetime.date | None = None
    message: str = DEFAULT_MESSAGE_TEMPLATE
    enabled: bool = True
