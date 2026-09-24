import datetime
from dataclasses import dataclass


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
    symbol: str
    signal: str = "risk-range"
    operator: str = "crossing-down"
    value: float | None = None
    frequency: str = "once_per_rearm"
    expires_at: datetime.date | None = None
    message: str = DEFAULT_MESSAGE_TEMPLATE
    enabled: bool = True
