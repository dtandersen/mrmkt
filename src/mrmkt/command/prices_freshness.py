"""Price freshness and bar-quality report over stored bars.

Flags are suspicion heuristics, not determinations:
- Stored bars are split- and dividend-adjusted with no adjustment
  provenance on StockPrice, so overnight gaps can suggest but never
  prove corporate actions.
- There is no exchange calendar in the repository; missing bars are
  measured against plain business days (Mon-Fri), which over-flags
  market holidays.
"""

from dataclasses import dataclass, field
from datetime import date, timedelta

from mrmkt.command._shared import normalize_tag, resolve_universe
from mrmkt.command.base import BaseResult, Command

GAP_JUMP_THRESHOLD = 0.20

LIMITATION_NOTES = (
    "limitations: corporate-action flags are suspicion heuristics "
    "(stored bars are split/dividend-adjusted with no adjustment "
    "provenance on StockPrice); missing bars are measured against "
    "Mon-Fri business days, so market holidays appear as missing"
)


@dataclass
class FreshnessQuery:
    today: date
    include_tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)
    lookback_days: int = 365
    stale_after_days: int = 5
    gap_threshold: float = GAP_JUMP_THRESHOLD


@dataclass
class FreshnessRow:
    symbol: str
    n_bars: int
    first_bar: date | None
    last_bar: date | None
    staleness_days: int | None
    expected_bars: int
    missing_bars: int
    flags: list[str] = field(default_factory=list)
    flag_details: str = ""


@dataclass
class FreshnessResult:
    today: date
    lookback_days: int
    stale_after_days: int
    gap_threshold: float
    include_tags: list[str]
    exclude_tags: list[str]
    universe_size: int
    rows: list[FreshnessRow]
    request: FreshnessQuery


@dataclass(frozen=True)
class CheckFreshnessRequest:
    tags: list[str] | None = None
    exclude_tags: list[str] | None = None
    lookback_days: int = 365
    stale_after_days: int = 5
    gap_threshold: float = GAP_JUMP_THRESHOLD


@dataclass
class CheckFreshnessResult(BaseResult[FreshnessResult]):
    pass


class CheckFreshness(Command[CheckFreshnessRequest, CheckFreshnessResult]):
    """Report price staleness and bar-quality flags over stored bars."""

    def __init__(self, repository, clock):
        self.repository = repository
        self.clock = clock

    def execute(self, request: CheckFreshnessRequest) -> CheckFreshnessResult:
        if request.lookback_days < 1:
            return CheckFreshnessResult.invalid_data(
                ["--lookback-days must be at least 1"]
            )
        if request.stale_after_days < 0:
            return CheckFreshnessResult.invalid_data(["--stale-after must be >= 0"])
        if request.gap_threshold <= 0:
            return CheckFreshnessResult.invalid_data(
                ["--gap-threshold must be positive"]
            )
        try:
            query = FreshnessQuery(
                include_tags=[normalize_tag(tag) for tag in (request.tags or [])],
                exclude_tags=[
                    normalize_tag(tag) for tag in (request.exclude_tags or [])
                ],
                today=self.clock.today(),
                lookback_days=request.lookback_days,
                stale_after_days=request.stale_after_days,
                gap_threshold=request.gap_threshold,
            )
        except ValueError as error:
            return CheckFreshnessResult.invalid_data([str(error)])
        try:
            outcome = self._score(query)
        except Exception as error:
            return CheckFreshnessResult.error([f"Failed to check freshness: {error}"])
        return CheckFreshnessResult.success(outcome)

    def _score(self, query: FreshnessQuery) -> FreshnessResult:
        """Score each universe symbol over the lookback window."""
        today = query.today
        symbols = resolve_universe(
            self.repository, query.include_tags, query.exclude_tags
        )
        window_start = today - timedelta(days=query.lookback_days)
        bars_by_symbol: dict = {}
        for price in self.repository.list_prices_for_symbols(symbols, date.min, today):
            bars_by_symbol.setdefault(price.symbol, []).append(price)

        rows: list[FreshnessRow] = []
        for symbol in symbols:
            bars = sorted(bars_by_symbol.get(symbol, []), key=lambda b: b.date)
            window = [b for b in bars if window_start <= b.date <= today]
            if not bars:
                rows.append(
                    FreshnessRow(
                        symbol=symbol,
                        n_bars=0,
                        first_bar=None,
                        last_bar=None,
                        staleness_days=None,
                        expected_bars=0,
                        missing_bars=0,
                        flags=["NO_BARS"],
                        flag_details="no stored bars at all",
                    )
                )
                continue
            last_bar = bars[-1].date
            staleness = (today - last_bar).days
            span_start = max(bars[0].date, window_start)
            expected = _business_days(span_start, min(last_bar, today))
            present = {b.date for b in window}
            missing = [d for d in expected if d not in present]
            flags: list[str] = []
            details: list[str] = []
            if staleness > query.stale_after_days:
                flags.append("STALE")
                details.append(f"last bar {last_bar.isoformat()} ({staleness}d ago)")
            if missing:
                flags.append("GAPS")
                details.append(
                    f"{len(missing)} missing business-day bars "
                    f"(first {missing[0].isoformat()}; holidays over-flagged)"
                )
            violations = [
                b.date.isoformat()
                for b in window
                if b.high < b.low
                or not (b.low <= b.close <= b.high)
                or not (b.low <= b.open <= b.high)
                or min(b.open, b.high, b.low, b.close) <= 0
            ]
            if violations:
                flags.append("OHLC_VIOLATION")
                details.append(f"bad bars: {','.join(violations[:5])}")
            zero_vol = [b.date.isoformat() for b in window if b.volume == 0]
            if zero_vol:
                flags.append("ZERO_VOLUME")
                details.append(f"zero volume: {','.join(zero_vol[:5])}")
            neg_vol = [b.date.isoformat() for b in window if b.volume < 0]
            if neg_vol:
                flags.append("NEGATIVE_VOLUME")
                details.append(f"negative volume: {','.join(neg_vol[:5])}")
            jumps = []
            prior = None
            for b in window:
                if prior is not None and prior.close > 0 and b.open > 0:
                    move = abs(b.open / prior.close - 1)
                    if move >= query.gap_threshold:
                        jumps.append(f"{b.date.isoformat()} ({move:.0%})")
                prior = b
            if jumps:
                flags.append("GAP_JUMP_HEURISTIC")
                details.append(
                    "overnight gaps >= "
                    f"{query.gap_threshold:.0%}: {','.join(jumps[:5])} "
                    "(suspicious, NOT proof of splits/actions)"
                )
            rows.append(
                FreshnessRow(
                    symbol=symbol,
                    n_bars=len(bars),
                    first_bar=bars[0].date,
                    last_bar=last_bar,
                    staleness_days=staleness,
                    expected_bars=len(expected),
                    missing_bars=len(missing),
                    flags=flags,
                    flag_details="; ".join(details),
                )
            )
        return FreshnessResult(
            today=today,
            lookback_days=query.lookback_days,
            stale_after_days=query.stale_after_days,
            gap_threshold=query.gap_threshold,
            include_tags=sorted(query.include_tags),
            exclude_tags=sorted(query.exclude_tags),
            universe_size=len(symbols),
            rows=sorted(rows, key=lambda r: r.symbol),
            request=query,
        )


def _business_days(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return days


FRESHNESS_COLUMNS = [
    "symbol",
    "n_bars",
    "first_bar",
    "last_bar",
    "staleness_days",
    "expected_bars",
    "missing_bars",
    "flags",
    "flag_details",
]


def render_csv(result: FreshnessResult) -> str:
    """Deterministic CSV: `# key=value` header, then per-symbol rows."""
    lines = [
        "# generator=mrmkt prices freshness",
        f"# today={result.today.isoformat()}",
        f"# lookback_days={result.lookback_days}",
        f"# stale_after_days={result.stale_after_days}",
        f"# gap_threshold={result.gap_threshold}",
        f"# universe_tags={','.join(result.include_tags) or '(all)'}",
        f"# universe_exclude_tags={','.join(result.exclude_tags) or '(none)'}",
        f"# universe_size={result.universe_size}",
        "# universe_membership_vintage=current (tag assignments)",
        f"# {LIMITATION_NOTES}",
    ]
    lines.append(",".join(FRESHNESS_COLUMNS))
    for row in result.rows:
        details = row.flag_details.replace(",", ";")
        lines.append(
            ",".join(
                [
                    row.symbol,
                    str(row.n_bars),
                    row.first_bar.isoformat() if row.first_bar else "",
                    row.last_bar.isoformat() if row.last_bar else "",
                    str(row.staleness_days) if row.staleness_days is not None else "",
                    str(row.expected_bars),
                    str(row.missing_bars),
                    "|".join(row.flags),
                    f'"{details}"' if details else "",
                ]
            )
        )
    return "\n".join(lines) + "\n"
