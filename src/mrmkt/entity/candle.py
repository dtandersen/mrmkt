import datetime as dt
from dataclasses import dataclass


@dataclass
class Candle:
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None
    datetime: dt.datetime | None = None
