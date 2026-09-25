"""Shared base for indicator-series commands (no Typer, no repository construction)."""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from mrmkt.command._shared import parse_cli_date

_SYMBOL_PATTERN = re.compile(r"[A-Z0-9]+(?:[./-][A-Z0-9]+)*")


@dataclass(frozen=True)
class IndicatorPoint:
    """One aligned row: bar date/close plus the computed column values."""

    date: date
    close: float
    values: tuple[float, ...]


@dataclass(frozen=True)
class IndicatorSeriesResult:
    """Column labels plus aligned points; the CLI renders them verbatim."""

    columns: tuple[str, ...]
    points: tuple[IndicatorPoint, ...]


class IndicatorSeries:
    """Validate args, load bars, align values; subclasses pin the indicator."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def _run(
        self,
        symbol: str,
        from_date: str | None,
        to_date: str | None,
        columns: tuple[str, ...],
        calculate: Callable[[list[float]], list[Any]],
        flatten: Callable[[Any], tuple[float, ...]],
        warmup_bars: int,
    ) -> IndicatorSeriesResult:
        normalized_symbol = symbol.upper()
        if _SYMBOL_PATTERN.fullmatch(normalized_symbol) is None:
            raise ValueError(f"invalid stock symbol: {symbol}")
        today = self.clock.today()
        try:
            start_date = (
                parse_cli_date(from_date, today) if from_date is not None else None
            )
            end_date = (
                parse_cli_date(to_date, today)
                if to_date is not None
                else today
            )
        except ValueError as error:
            raise ValueError(
                "dates must be ISO dates, now, or durations such as 180d"
            ) from error
        if start_date is not None and start_date > end_date:
            raise ValueError("--from must be on or before --to")

        prices = sorted(
            self.repository.list_prices(normalized_symbol, date.min, end_date),
            key=lambda price: price.date,
        )
        values = calculate([price.close for price in prices])
        aligned_prices = prices[warmup_bars : warmup_bars + len(values)]
        points = tuple(
            IndicatorPoint(
                date=price.date, close=price.close, values=flatten(value)
            )
            for price, value in zip(aligned_prices, values, strict=True)
            if start_date is None or price.date >= start_date
        )
        return IndicatorSeriesResult(columns=columns, points=points)
