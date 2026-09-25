"""Deterministic risk-range bands from stored bars."""

from dataclasses import dataclass
from datetime import date

from mrmkt.command._shared import (
    _resolve_signal,
    normalize_symbol,
    normalize_tag,
    parse_cli_date,
    resolve_universe,
)
from mrmkt.command.alerts import (
    DEFAULT_ANCHOR,
    DEFAULT_HORIZON,
    DEFAULT_VOL_PERIOD,
    DEFAULT_WIDTH,
    MIN_BARS,
    LevelRow,
    LevelsResult,
)
from mrmkt.command.base import BaseResult, Command
from mrmkt.indicator.risk_range import risk_range_series


@dataclass
class LevelsQuery:
    include_tags: list[str]
    symbols: list[str]
    as_of: date | None
    horizon: int
    vol_period: int
    width: float
    anchor_period: int


@dataclass(frozen=True)
class ListRangesRequest:
    symbols: list[str] | None = None
    tags: list[str] | None = None
    signal: str = "risk-range"
    as_of: str | None = None
    horizon: int = DEFAULT_HORIZON
    vol_period: int = DEFAULT_VOL_PERIOD
    width: float = DEFAULT_WIDTH
    anchor_period: int = DEFAULT_ANCHOR


@dataclass
class ListRangesResult(BaseResult[LevelsResult]):
    pass


class ListRanges(Command[ListRangesRequest, ListRangesResult]):
    """Print deterministic risk-range buy/sell levels from stored bars."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(self, request: ListRangesRequest) -> ListRangesResult:
        try:
            _resolve_signal(request.signal)
        except ValueError as error:
            return ListRangesResult.invalid_data([str(error)])
        if not request.symbols and not request.tags:
            return ListRangesResult.invalid_data(["provide symbols or --tag"])
        today = self.clock.today()
        try:
            as_of_date = (
                parse_cli_date(request.as_of, today)
                if request.as_of is not None
                else None
            )
        except ValueError:
            return ListRangesResult.invalid_data(
                ["dates must be ISO dates, now, or durations such as 180d"]
            )
        try:
            include_tags = [normalize_tag(tag) for tag in (request.tags or [])]
            normalized_symbols = [
                normalize_symbol(symbol) for symbol in (request.symbols or [])
            ]
        except ValueError as error:
            return ListRangesResult.invalid_data([str(error)])
        try:
            outcome = self._levels(
                LevelsQuery(
                    include_tags=include_tags,
                    symbols=normalized_symbols,
                    as_of=as_of_date,
                    horizon=request.horizon,
                    vol_period=request.vol_period,
                    width=request.width,
                    anchor_period=request.anchor_period,
                )
            )
        except Exception as error:
            return ListRangesResult.error([f"Failed to compute levels: {error}"])
        return ListRangesResult.success(outcome)

    def _levels(self, query: LevelsQuery) -> LevelsResult:
        """Compute one range per symbol from bars on/before as-of."""
        explicit = {s.strip().upper() for s in query.symbols}
        if query.include_tags:
            universe = resolve_universe(self.repository, query.include_tags, [])
            wanted = sorted(set(universe) | explicit)
        else:
            # Explicit symbols alone: never fall back to the whole catalog.
            wanted = sorted(explicit)
        as_of = query.as_of
        bars_by_symbol: dict = {}
        for price in self.repository.list_prices_for_symbols(
            wanted, date.min, as_of if as_of is not None else date.max
        ):
            if as_of is not None and price.date > as_of:
                continue
            bars_by_symbol.setdefault(price.symbol, []).append(price)
        if as_of is None:
            known = [b.date for bars in bars_by_symbol.values() for b in bars]
            as_of = max(known) if known else None
        rows: list[LevelRow] = []
        for symbol in wanted:
            bars = sorted(
                (
                    b
                    for b in bars_by_symbol.get(symbol, [])
                    if as_of is None or b.date <= as_of
                ),
                key=lambda b: b.date,
            )
            if len(bars) < MIN_BARS:
                continue
            closes = [b.close for b in bars]
            try:
                ranges = risk_range_series(
                    closes,
                    query.horizon,
                    query.vol_period,
                    query.width,
                    query.anchor_period,
                )
            except ValueError:
                continue
            if not ranges:
                continue
            latest = ranges[-1]
            rows.append(
                LevelRow(
                    symbol=symbol,
                    as_of=bars[-1].date,
                    close=bars[-1].close,
                    range_low=latest.low,
                    range_high=latest.high,
                    n_bars=len(bars),
                )
            )
        vintage = max((r.as_of for r in rows), default=None)
        return LevelsResult(
            as_of=as_of,
            data_vintage=vintage,
            horizon=query.horizon,
            vol_period=query.vol_period,
            width=query.width,
            anchor_period=query.anchor_period,
            include_tags=sorted(query.include_tags),
            symbols=wanted,
            rows=sorted(rows, key=lambda r: r.symbol),
        )
