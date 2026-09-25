"""Deterministic risk-range bands from stored bars."""

from mrmkt.command._shared import (
    _resolve_signal,
    normalize_symbol,
    normalize_tag,
    parse_cli_date,
)
from mrmkt.command.alerts import LevelsUseCase


class ListRanges:
    """Print deterministic risk-range buy/sell levels from stored bars."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(
        self,
        symbols: list[str] | None,
        tags: list[str] | None,
        signal: str,
        as_of: str | None,
        horizon: int,
        vol_period: int,
        width: float,
        anchor_period: int,
    ):
        _resolve_signal(signal)
        if not symbols and not tags:
            raise ValueError("provide symbols or --tag")
        today = self.clock.today()
        try:
            as_of_date = parse_cli_date(as_of, today) if as_of is not None else None
        except ValueError as error:
            raise ValueError("dates must be ISO dates, now, or durations such as 180d") from error
        try:
            include_tags = [normalize_tag(tag) for tag in (tags or [])]
            normalized_symbols = [
                normalize_symbol(symbol) for symbol in (symbols or [])
            ]
        except ValueError as error:
            # Tag/symbol normalization failures surface through the generic
            # failure path like before.
            raise RuntimeError(str(error)) from error
        return LevelsUseCase(self.repository).execute(
            include_tags=include_tags,
            symbols=normalized_symbols,
            as_of=as_of_date,
            horizon=horizon,
            vol_period=vol_period,
            width=width,
            anchor_period=anchor_period,
        )
