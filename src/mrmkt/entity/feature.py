"""Computed per-symbol feature (screening inputs, logged daily)."""

import datetime
from dataclasses import dataclass


@dataclass
class Feature:
    """One feature value: feature names carry params (e.g. ``rr15.low``).

    ``date`` is the bar the value describes; ``computed_at`` is when it
    ran. Numeric features use ``value_num``, flags/labels ``value_text``.
    """

    symbol: str
    exchange: str
    feature: str
    date: datetime.date
    value_num: float | None = None
    value_text: str | None = None
    computed_at: datetime.datetime | None = None
