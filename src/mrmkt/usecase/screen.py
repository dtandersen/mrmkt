"""Point-in-time technical screener over the tagged price catalog.

Every metric for a symbol uses only bars on or before ``as_of``.
Universe membership comes from current tag assignments: the repository
carries no historical tag snapshots, so the membership vintage is
reported as ``current`` and the historical universe itself must NOT be
called point-in-time. Fundamentals are structurally unavailable (no
populated pipeline), so only ``technical-only`` mode exists.
"""

import statistics
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from mrmkt.indicator.sma import sma
from mrmkt.indicator.volatility import volatility
from mrmkt.usecase.universe import MEMBERSHIP_VINTAGE_NOTE, resolve_universe

SUPPORTED_MODES = ("technical-only",)

MOM_LOOKBACK = 126
MOM_SKIP = 5
VOL_PERIOD = 21
TREND_FAST = 63
TREND_SLOW = 200
PULLBACK_PERIOD = 20
DVOL_WINDOW = 63
PULLBACK_CAP = 0.10

SCORE_FORMULA = (
    "score=0.4*mom_rank+0.25*trend_frac+0.2*pullback_depth_capped"
    "+0.15*(1-vol_rank); mom=126D return skipping 5D"
)

FIXED_INPUTS = (
    "sma_periods=20/63/200; mom_lookback=126; mom_skip=5; vol_period=21; "
    "pullback_period=20; pullback_cap=0.10; dollar_vol_window=63; "
    "weights=mom:0.4,trend:0.25,pullback:0.2,lowvol:0.15"
)


@dataclass
class ScreenRequest:
    include_tags: list[str] = field(default_factory=list)
    exclude_tags: list[str] = field(default_factory=list)
    as_of: date | None = None
    mode: str = "technical-only"
    min_price: float = 0.0
    min_dollar_vol: float = 0.0
    min_bars: int = 0
    max_stale_days: int | None = None
    top_n: int | None = None


@dataclass
class ScreenRow:
    symbol: str
    last_date: date
    last_close: float
    n_bars: int
    sma20: float | None
    sma63: float | None
    sma200: float | None
    dist_sma20: float | None
    momentum: float
    vol_21: float
    dollar_vol_med63: float | None
    trend_points: int = 0
    pullback_depth: float = 0.0
    score: float = 0.0
    rank: int = 0


@dataclass
class ScreenResult:
    as_of: date
    data_vintage: date | None
    include_tags: list[str]
    exclude_tags: list[str]
    universe_size: int
    excluded: dict[str, int]
    rows: list[ScreenRow]
    request: ScreenRequest


def _sma(values: list[float], period: int) -> float | None:
    """Trailing mean via the shared indicator definition."""
    if len(values) < period:
        return None
    return sma(values, period)[-1]


def _realized_vol(closes: list[float], period: int) -> float | None:
    """Annualized trailing volatility via the shared indicator definition."""
    if len(closes) < period + 1:
        return None
    try:
        return volatility(closes, period)[-1]
    except (ValueError, IndexError):
        return None


def _pct_rank(values: list[float]) -> list[float]:
    """Cross-sectional percentile ranks in [0, 1]; ties share the mean rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    pos = 0
    while pos < len(order):
        tie_end = pos
        while tie_end + 1 < len(order) and values[order[tie_end + 1]] == values[order[pos]]:
            tie_end += 1
        mean_rank = (pos + tie_end) / 2 / max(len(values) - 1, 1)
        for k in range(pos, tie_end + 1):
            ranks[order[k]] = mean_rank
        pos = tie_end + 1
    return ranks


class ScreenUseCase:
    """Rank a tag universe on as-of technicals; no ad hoc SQL."""

    def __init__(self, repository):
        self.repository = repository

    def execute(self, request: ScreenRequest) -> ScreenResult:
        """Run the screen; all inputs echo back in the result/CSV."""
        if request.mode not in SUPPORTED_MODES:
            raise ValueError(
                f"unknown mode {request.mode!r} (choose from {list(SUPPORTED_MODES)}; "
                "fundamentals are unavailable: no populated pipeline)"
            )
        if request.min_price < 0 or request.min_dollar_vol < 0 or request.min_bars < 0:
            raise ValueError("min_price, min_dollar_vol, and min_bars must be >= 0")
        if request.top_n is not None and request.top_n < 1:
            raise ValueError("top_n must be at least 1")
        if request.max_stale_days is not None and request.max_stale_days < 0:
            raise ValueError("max_stale_days must be >= 0")

        symbols = resolve_universe(
            self.repository, request.include_tags, request.exclude_tags
        )

        as_of = request.as_of
        bars_by_symbol: dict = {}
        for price in self.repository.list_prices_for_symbols(
            symbols, date.min, as_of if as_of is not None else date.max
        ):
            if as_of is not None and price.date > as_of:
                continue
            bars_by_symbol.setdefault(price.symbol, []).append(price)

        if as_of is None:
            known_dates = [bar.date for bars in bars_by_symbol.values() for bar in bars]
            resolved = max(known_dates) if known_dates else None
            if resolved is None:
                return ScreenResult(
                    as_of=None,  # type: ignore[arg-type]
                    data_vintage=None,
                    include_tags=sorted(request.include_tags),
                    exclude_tags=sorted(request.exclude_tags),
                    universe_size=0,
                    excluded={},
                    rows=[],
                    request=request,
                )
            as_of = resolved

        # Vintage spans the entire screened price universe (bars <= as-of
        # for every selected symbol), computed before any truncation, so a
        # top_n cut cannot conceal newer bars elsewhere in the universe.
        vintage_dates = [
            bar.date for bars in bars_by_symbol.values() for bar in bars if bar.date <= as_of
        ]
        vintage = max(vintage_dates) if vintage_dates else None

        candidates: list[ScreenRow] = []
        excluded: dict[str, int] = {}

        def _exclude(reason: str) -> None:
            excluded[reason] = excluded.get(reason, 0) + 1

        for symbol in symbols:
            bars = sorted(bars_by_symbol.get(symbol, []), key=lambda b: b.date)
            bars = [b for b in bars if b.date <= as_of]
            if len(bars) < max(request.min_bars, MOM_LOOKBACK + MOM_SKIP + 1, TREND_SLOW):
                # Fixed formation windows keep the screen comparable;
                # min_bars can only raise this floor, never lower it.
                _exclude("short_history")
                continue
            closes = [b.close for b in bars]
            vols = [b.volume for b in bars]
            last = bars[-1]
            if request.max_stale_days is not None and (as_of - last.date).days > request.max_stale_days:
                # Opt-in recency gate; calendar-day difference, so a Friday
                # bar screened on Monday is 3 days stale. Stale names stay
                # listed by default; pair with `prices freshness` instead.
                _exclude("stale")
                continue
            if last.close < request.min_price:
                _exclude("min_price")
                continue
            dvol = statistics.median(
                c * v
                for c, v in zip(closes[-DVOL_WINDOW:], vols[-DVOL_WINDOW:], strict=True)
            )
            if dvol < request.min_dollar_vol:
                _exclude("min_dollar_vol")
                continue
            sma20 = _sma(closes, PULLBACK_PERIOD)
            sma63 = _sma(closes, TREND_FAST)
            sma200 = _sma(closes, TREND_SLOW)
            dist_sma20 = (last.close - sma20) / sma20 if sma20 else None
            momentum = closes[-1 - MOM_SKIP] / closes[-1 - MOM_SKIP - MOM_LOOKBACK] - 1
            vol_21 = _realized_vol(closes, VOL_PERIOD)
            if vol_21 is None:
                _exclude("vol_unavailable")
                continue
            trend_points = sum(
                1
                for level in (sma63, sma200)
                if level is not None and last.close > level
            )
            depth = max(0.0, min(1.0, ((sma20 - last.close) / sma20) / PULLBACK_CAP)) if sma20 else 0.0
            candidates.append(
                ScreenRow(
                    symbol=symbol,
                    last_date=last.date,
                    last_close=last.close,
                    n_bars=len(bars),
                    sma20=sma20,
                    sma63=sma63,
                    sma200=sma200,
                    dist_sma20=dist_sma20,
                    momentum=momentum,
                    vol_21=vol_21,
                    dollar_vol_med63=dvol,
                    trend_points=trend_points,
                    pullback_depth=depth,
                )
            )

        if candidates:
            mom_ranks = _pct_rank([c.momentum for c in candidates])
            vol_ranks = _pct_rank([c.vol_21 for c in candidates])
            for row, mom_rank, vol_rank in zip(candidates, mom_ranks, vol_ranks, strict=True):
                row.score = (
                    0.4 * mom_rank
                    + 0.25 * (row.trend_points / 2)
                    + 0.2 * row.pullback_depth
                    + 0.15 * (1 - vol_rank)
                )
            ordered = sorted(candidates, key=lambda r: (-r.score, r.symbol))
        else:
            ordered = []
        if request.top_n is not None:
            ordered = ordered[: request.top_n]
        for pos, row in enumerate(ordered, start=1):
            row.rank = pos
        return ScreenResult(
            as_of=as_of,
            data_vintage=vintage,
            include_tags=sorted(request.include_tags),
            exclude_tags=sorted(request.exclude_tags),
            universe_size=len(symbols),
            excluded=excluded,
            rows=ordered,
            request=request,
        )


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float):
        return repr(value)
    return str(value)


SCREEN_COLUMNS = [
    "rank",
    "symbol",
    "last_date",
    "last_close",
    "n_bars",
    "sma20",
    "sma63",
    "sma200",
    "dist_sma20",
    "momentum_126_5",
    "vol_21",
    "dollar_vol_med63",
    "trend_points",
    "pullback_depth",
    "score",
]


def render_csv(result: ScreenResult) -> str:
    """Deterministic CSV: `# key=value` input/vintage header, then rows."""
    req = result.request
    lines = [
        "# generator=mrmkt screen",
        f"# mode={req.mode}",
        f"# as_of={result.as_of.isoformat() if result.as_of else ''}",
        f"# data_vintage={result.data_vintage.isoformat() if result.data_vintage else ''}",
        f"# universe_tags={','.join(result.include_tags) or '(all)'}",
        f"# universe_exclude_tags={','.join(result.exclude_tags) or '(none)'}",
        f"# universe_size={result.universe_size}",
        f"# universe_membership_vintage={MEMBERSHIP_VINTAGE_NOTE}",
        f"# min_price={req.min_price}",
        f"# min_dollar_vol={req.min_dollar_vol}",
        f"# min_bars={req.min_bars}",
        f"# max_stale_days={req.max_stale_days if req.max_stale_days is not None else ''}",
        f"# top_n={req.top_n if req.top_n is not None else ''}",
        f"# excluded_total={sum(result.excluded.values())}",
        *[
            f"# excluded_{reason}={count}"
            for reason, count in sorted(result.excluded.items())
        ],
        f"# {SCORE_FORMULA}",
        f"# fixed_inputs: {FIXED_INPUTS}",
        "# fundamentals=unavailable (no populated pipeline; technical-only)",
    ]
    lines.append(",".join(SCREEN_COLUMNS))
    for row in result.rows:
        lines.append(
            ",".join(
                [
                    str(row.rank),
                    row.symbol,
                    row.last_date.isoformat(),
                    _fmt(row.last_close),
                    str(row.n_bars),
                    _fmt(row.sma20),
                    _fmt(row.sma63),
                    _fmt(row.sma200),
                    _fmt(row.dist_sma20),
                    _fmt(row.momentum),
                    _fmt(row.vol_21),
                    _fmt(row.dollar_vol_med63),
                    str(row.trend_points),
                    _fmt(row.pullback_depth),
                    _fmt(row.score),
                ]
            )
        )
    return "\n".join(lines) + "\n"
