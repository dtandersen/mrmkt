"""Realtime risk-range alerts over stored levels and live price ticks.

Levels come from the shared ``risk_range_series`` definition as of the
last stored close (defaults H=15/V=21/W=0.5/anchor=5). Triggers are
timing information only: they are not advice, not orders, and no fill
at a level is guaranteed. Signal bars and live prints differ — a stored
daily bar close is history, a live tick is now; the CSV and trigger
lines keep the two apart.
"""

import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime

import requests

from mrmkt.command._shared import MEMBERSHIP_VINTAGE_NOTE, resolve_universe
from mrmkt.common.clock import ET
from mrmkt.indicator.risk_range import risk_range_series

DEFAULT_HORIZON = 15
DEFAULT_VOL_PERIOD = 21
DEFAULT_WIDTH = 0.5
DEFAULT_ANCHOR = 5
MIN_BARS = 30

WEBHOOK_ENV_VAR = "MRMKT_ALERTS_WEBHOOK_URL"  # reserved; ntfy is the supported remote sink
NTFY_ENV_VAR = "MRMKT_ALERTS_NTFY_URL"
NTFY_CONFIG_KEYS = ("ntfy", "nfty")  # nfty: legacy misspelling, still honored
NTFY_DEFAULT_HOST = "https://ntfy.sh"


def session_at(moment: datetime) -> str:
    """Classify a moment as regular/pre/post/closed (US Eastern).

    Weekends are always closed. There is no exchange-holiday calendar in
    the repo, so holidays misclassify as sessions; the stream delivers
    nothing on holidays and arming is unaffected.
    """
    eastern = moment.astimezone(ET)
    if eastern.weekday() >= 5:
        return "closed"
    minutes = eastern.hour * 60 + eastern.minute
    if minutes < 4 * 60:
        return "closed"
    if minutes < 9 * 60 + 30:
        return "pre"
    if minutes < 16 * 60:
        return "regular"
    if minutes < 20 * 60:
        return "post"
    return "closed"


@dataclass
class LevelRow:
    symbol: str
    as_of: date
    close: float
    range_low: float
    range_high: float
    n_bars: int


@dataclass
class LevelsResult:
    as_of: date | None
    data_vintage: date | None
    horizon: int
    vol_period: int
    width: float
    anchor_period: int
    include_tags: list[str]
    symbols: list[str]
    rows: list[LevelRow]


class LevelsUseCase:
    """Deterministic buy/sell levels from stored bars; no ad hoc SQL."""

    def __init__(self, repository):
        self.repository = repository

    def execute(
        self,
        include_tags: list[str],
        symbols: list[str],
        as_of: date | None = None,
        horizon: int = DEFAULT_HORIZON,
        vol_period: int = DEFAULT_VOL_PERIOD,
        width: float = DEFAULT_WIDTH,
        anchor_period: int = DEFAULT_ANCHOR,
    ) -> LevelsResult:
        """Compute one range per symbol from bars on/before as-of."""
        explicit = {s.strip().upper() for s in symbols}
        if include_tags:
            universe = resolve_universe(self.repository, include_tags, [])
            wanted = sorted(set(universe) | explicit)
        else:
            # Explicit symbols alone: never fall back to the whole catalog.
            wanted = sorted(explicit)
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
                (b for b in bars_by_symbol.get(symbol, []) if as_of is None or b.date <= as_of),
                key=lambda b: b.date,
            )
            if len(bars) < MIN_BARS:
                continue
            closes = [b.close for b in bars]
            try:
                ranges = risk_range_series(closes, horizon, vol_period, width, anchor_period)
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
            horizon=horizon,
            vol_period=vol_period,
            width=width,
            anchor_period=anchor_period,
            include_tags=sorted(include_tags),
            symbols=wanted,
            rows=sorted(rows, key=lambda r: r.symbol),
        )


LEVELS_COLUMNS = ["symbol", "as_of", "close", "range_low", "range_high", "n_bars"]


def render_levels_csv(result: LevelsResult) -> str:
    """Deterministic CSV: `# key=value` header, then per-symbol levels."""
    lines = [
        "# generator=mrmkt ranges",
        f"# as_of={result.as_of.isoformat() if result.as_of else ''}",
        f"# data_vintage={result.data_vintage.isoformat() if result.data_vintage else ''}",
        f"# range=H{result.horizon}/V{result.vol_period}/W{result.width:g}/anchor{result.anchor_period}",
        f"# universe_tags={','.join(result.include_tags) or '(none)'}",
        f"# universe_symbols={','.join(result.symbols) or '(none)'}",
        f"# universe_membership_vintage={MEMBERSHIP_VINTAGE_NOTE}",
        "# note=ranges are timing information only, not advice; no fill at a level is guaranteed",
    ]
    lines.append(",".join(LEVELS_COLUMNS))
    for row in result.rows:
        lines.append(
            ",".join(
                [
                    row.symbol,
                    row.as_of.isoformat(),
                    repr(row.close),
                    repr(row.range_low),
                    repr(row.range_high),
                    str(row.n_bars),
                ]
            )
        )
    return "\n".join(lines) + "\n"


@dataclass
class Alert:
    symbol: str
    moment: datetime
    session: str
    price: float
    level: float
    text: str | None = None


@dataclass
class IgnoredTick:
    """Below-level tick that could not fire under the session policy."""

    symbol: str
    moment: datetime
    session: str
    price: float
    level: float
    reason: str


@dataclass
class TriggerRule:
    """Per-symbol evaluation rule for one stored trigger.

    Operators mirror the common alert vocabulary: ``crossing-down`` /
    ``crossing-up`` fire on an observed transition across the level,
    ``greater-than`` / ``less-than`` fire while the price holds beyond
    the level. Frequencies: ``once_per_rearm`` fires on entry into the
    firing side and needs the opposite side to re-arm; ``once`` fires a
    single time and never re-arms; ``every_time`` fires on every
    in-policy tick while the condition holds. ``expires_at`` disables
    firing after that date. ``message`` is a ``str.format`` template
    with ``{symbol}`` ``{price}`` ``{level}`` ``{moment}`` ``{session}``
    placeholders (empty means the default trigger line).
    """

    operator: str = "crossing-down"
    frequency: str = "once_per_rearm"
    expires_at: date | None = None
    message: str = ""


DEFAULT_RULE = TriggerRule()


def render_message(template: str, *, symbol: str, price: float, level: float, moment: datetime, session: str) -> str:
    """Render a trigger message template; falls back to the default line."""
    try:
        return template.format(
            symbol=symbol,
            price=price,
            level=level,
            moment=moment.isoformat(),
            session=session,
        )
    except (KeyError, ValueError, AttributeError, IndexError):
        return format_alert(Alert(symbol, moment, session, price, level))


@dataclass
class AlertEngine:
    """Transition-only triggers with re-arm; state is in-memory.

    Unknown symbols start with no baseline: the first tick only
    establishes above/below state and never fires. ``seed_baseline``
    seeds state from stored closes so an opening gap across the level
    fires once on its first regular-session print. Ticks outside the
    trigger sessions never fire and never disarm; an above-level tick
    re-arms in any session. Every non-firing below-level tick outside
    the trigger sessions is recorded in ``ignored`` (never silently
    dropped). ``session_policy`` is ``regular`` (default) or
    ``extended`` (pre/post also fire, lines stay session-labeled).
    """

    on_alert: Callable[[Alert], None]
    on_ignored: Callable[[IgnoredTick], None] | None = None
    armed: dict[str, bool | None] = field(default_factory=dict)
    levels: dict[str, float] = field(default_factory=dict)
    rules: dict[str, TriggerRule] = field(default_factory=dict)
    spent: set[str] = field(default_factory=set)
    frozen: set[str] = field(default_factory=set)
    session_policy: str = "regular"
    histories: dict[str, list[float]] = field(default_factory=dict)
    last_bar_dates: dict[str, date] = field(default_factory=dict)
    range_params: tuple = (
        DEFAULT_HORIZON,
        DEFAULT_VOL_PERIOD,
        DEFAULT_WIDTH,
        DEFAULT_ANCHOR,
    )
    ignored: list[IgnoredTick] = field(default_factory=list)

    def __post_init__(self):
        if self.session_policy not in ("regular", "extended"):
            raise ValueError(
                f"session_policy must be 'regular' or 'extended', "
                f"got {self.session_policy!r}"
            )

    def set_levels(self, levels: dict[str, float]) -> None:
        """(Re)set trigger levels; never resets arm state."""
        self.levels.update(levels)

    def set_rule(self, symbol: str, rule: TriggerRule) -> None:
        """Attach an evaluation rule; validates operator/frequency."""
        if rule.operator not in ("crossing-down", "crossing-up", "greater-than", "less-than"):
            raise ValueError(f"unknown operator {rule.operator!r}")
        if rule.frequency not in ("once_per_rearm", "once", "every_time"):
            raise ValueError(f"unknown frequency {rule.frequency!r}")
        self.rules[symbol] = rule

    def _seed_one(self, symbol: str, close: float | None) -> None:
        """Arm from a close vs the current level per the symbol's rule."""
        level = self.levels.get(symbol)
        if level is None or close is None:
            return
        rule = self.rules.get(symbol, DEFAULT_RULE)
        if rule.operator in ("crossing-down", "less-than"):
            self.armed[symbol] = bool(close > level)
        else:
            self.armed[symbol] = bool(close <= level)

    def seed_baseline(self, prior_closes: dict[str, float | None]) -> None:
        """Seed arm state from stored closes (e.g. LevelsRow.close).

        Prior close on the ready side arms the symbol, so a first
        regular-session print across the level fires as an opening-gap
        cross. A prior close already past the level (or unknown) leaves
        it disarmed (or unknown) until a later re-cross.
        """
        for symbol, prior in prior_closes.items():
            self._seed_one(symbol, prior)

    def set_history(
        self, symbol: str, closes: list[float], last_bar_date: date | None = None
    ) -> None:
        """Store per-symbol closes for daily-bar level recomputation."""
        self.histories[symbol] = list(closes)
        if last_bar_date is not None:
            self.last_bar_dates[symbol] = last_bar_date

    def roll_daily_bar(self, symbol: str, close: float, bar_date: date | None) -> float | None:
        """Roll a new daily close into history and recompute the level.

        Same-date updates are ignored (levels stay as-of the last stored
        close); only a strictly newer bar date recomputes. Returns the
        new buy level, or None when nothing changed. Recomputation also
        re-seeds the armed state from the new bar close vs the new level,
        so a threshold moving above a stale print cannot fire without a
        live above-to-below crossing.
        """
        history = self.histories.get(symbol)
        if history is None:
            return None
        if symbol in self.frozen:
            return None
        if bar_date is not None:
            last = self.last_bar_dates.get(symbol)
            if last is not None and bar_date <= last:
                return None
            self.last_bar_dates[symbol] = bar_date
        history = [*history, close]
        self.histories[symbol] = history
        horizon, vol_period, width, anchor = self.range_params
        try:
            ranges = risk_range_series(history, horizon, vol_period, width, anchor)
        except ValueError:
            return None
        if not ranges:
            return None
        self.levels[symbol] = ranges[-1].low
        self._seed_one(symbol, close)
        return ranges[-1].low

    def trigger_sessions(self) -> tuple:
        """Sessions whose ticks may fire under the configured policy."""
        if self.session_policy == "extended":
            return ("regular", "pre", "post")
        return ("regular",)

    def _fire(
        self, symbol: str, price: float, moment: datetime, session: str, level: float, rule: TriggerRule
    ) -> Alert:
        """Emit an alert; ``once`` rules never re-arm afterwards."""
        if rule.frequency == "once":
            self.spent.add(symbol)
        self.armed[symbol] = False
        text = render_message(rule.message, symbol=symbol, price=price, level=level, moment=moment, session=session) if rule.message else None
        alert = Alert(symbol, moment, session, price, level, text=text)
        self.on_alert(alert)
        return alert

    def _ignore(self, symbol: str, price: float, moment: datetime, session: str, level: float, reason: str) -> None:
        """Record a non-firing tick explicitly (never silently dropped)."""
        tick = IgnoredTick(
            symbol=symbol,
            moment=moment,
            session=session,
            price=price,
            level=level,
            reason=reason,
        )
        self.ignored.append(tick)
        if self.on_ignored is not None:
            self.on_ignored(tick)

    def on_tick(self, symbol: str, price: float, moment: datetime) -> Alert | None:
        """Process one price tick; returns the Alert if one fires."""
        level = self.levels.get(symbol)
        if level is None:
            return None
        rule = self.rules.get(symbol, DEFAULT_RULE)
        session = session_at(moment)
        if rule.expires_at is not None and moment.date() > rule.expires_at:
            self._ignore(symbol, price, moment, session, level, "trigger expired")
            return None
        in_session = session in self.trigger_sessions()
        state = self.armed.get(symbol)
        if rule.operator in ("crossing-down", "less-than"):
            ready_side = price > level
        else:
            ready_side = price <= level
        if ready_side:
            if symbol not in self.spent:
                self.armed[symbol] = True
            return None
        if (
            rule.frequency == "every_time"
            and rule.operator in ("greater-than", "less-than")
        ):
            if in_session:
                return self._fire(symbol, price, moment, session, level, rule)
            self._ignore(
                symbol, price, moment, session, level,
                f"{session} tick ignored under {self.session_policy}-only policy",
            )
            return None
        if state and in_session:
            return self._fire(symbol, price, moment, session, level, rule)
        if state is None:
            self.armed[symbol] = False
        elif not in_session:
            self._ignore(
                symbol, price, moment, session, level,
                f"{session} tick ignored under {self.session_policy}-only policy",
            )
        return None


def format_alert(alert: Alert) -> str:
    """One deterministic trigger line (timestamps vary live, of course)."""
    if alert.text:
        return alert.text
    return (
        f"{alert.moment.isoformat()} | {alert.session} | {alert.symbol} | "
        f"{alert.price:g} <= buy {alert.level:g} TRIGGER"
    )


class ListSink:
    """In-memory sink for tests; also feeds real sinks."""

    def __init__(self):
        self.alerts: list[Alert] = []

    def __call__(self, alert: Alert) -> None:
        self.alerts.append(alert)


class StdoutSink:
    """Print trigger lines to stdout."""

    def __call__(self, alert: Alert) -> None:
        print(format_alert(alert), flush=True)


class FileSink:
    """Append trigger lines to a file; I/O errors go to stderr."""

    def __init__(self, path: str):
        self.path = path

    def __call__(self, alert: Alert) -> None:
        import sys

        try:
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(format_alert(alert) + "\n")
        except OSError as error:
            print(f"alert file sink failed: {error}", file=sys.stderr, flush=True)


def resolve_ntfy_url(env_value: str | None, config: dict | None = None) -> str:
    """Resolve the ntfy topic URL without ever logging it.

    Precedence: ``MRMKT_ALERTS_NTFY_URL`` env var, then local config
    ``ntfy`` key, then legacy misspelled ``nfty`` key. Config values
    may be a full URL or a bare topic (posted to the default host).
    Returns "" when nothing is configured.
    """
    if env_value and env_value.strip():
        return env_value.strip()
    cfg = config or {}
    for key in NTFY_CONFIG_KEYS:
        value = cfg.get(key)
        if isinstance(value, str) and value.strip():
            topic = value.strip()
            if "://" in topic:
                return topic
            return f"{NTFY_DEFAULT_HOST}/{topic}"
    return ""


class NtfySink:
    """ntfy notifications via raw-text POST (no JSON envelope).

    The topic URL (which contains the topic name) comes from the
    ``MRMKT_ALERTS_NTFY_URL`` environment variable only — never baked
    into the repo, docs, or CLI args. Triggers post at priority 4.
    """

    def __init__(self, url: str):
        if not url:
            raise ValueError(
                "ntfy URL must not be blank "
                f"(set {NTFY_ENV_VAR}, never the repo)"
            )
        _require_http_url(url)
        self.url = url

    def __call__(self, alert: Alert) -> None:
        headers = {
            "Title": f"{alert.symbol} below risk-range buy {alert.level:g}",
            "Priority": "4",
        }
        try:
            response = requests.post(
                self.url,
                data=format_alert(alert).encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            # Never log the error text: requests errors often embed the
            # full URL, which would expose the configured topic.
            status = error.response.status_code if error.response is not None else "no-response"
            print(
                f"alert ntfy sink failed: {type(error).__name__} status={status}",
                file=sys.stderr,
                flush=True,
            )


def _require_http_url(url: str) -> None:
    scheme = url.split("://", 1)[0].lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"sink URL must use http(s), got {scheme!r}")


class FanoutSink:
    """Deliver each alert to every configured sink."""

    def __init__(self, sinks: list):
        self.sinks = sinks

    def __call__(self, alert: Alert) -> None:
        for sink in self.sinks:
            sink(alert)


def dry_run_alerts(
    engine: AlertEngine,
    bars_by_symbol: dict,
    seed_bars: int = MIN_BARS,
    preset_levels: dict[str, float] | None = None,
) -> list[Alert]:
    """Replay stored daily lows as regular-session ticks, chronologically.

    Each symbol's level is initialized from its seed window
    (``risk_range_series(history[:seed_bars])[-1].low``) with arm state
    seeded from the seed close, unless ``preset_levels`` supplies an
    explicit level (used for stored triggers with fixed values; such
    symbols are frozen against daily recomputation). Each replay day
    compares the day's low against the level available from the prior
    close, then rolls the day's close afterward for the next session —
    never the reverse, so no same-bar information leaks into today's
    trigger. Delivery is the engine's ``on_alert`` only; the CLI wires
    a recording sink and prints 'would alert' lines, so ``--dry-run``
    can never touch real sinks.
    """
    fired: list[Alert] = []
    horizon, vol_period, width, anchor = engine.range_params
    preset_levels = preset_levels or {}
    for symbol in sorted(bars_by_symbol):
        bars = sorted(bars_by_symbol[symbol], key=lambda b: b.date)
        if len(bars) <= seed_bars:
            continue
        seed_ranges = risk_range_series(
            [b.close for b in bars[:seed_bars]], horizon, vol_period, width, anchor
        )
        if not seed_ranges:
            continue
        engine.set_history(
            symbol,
            [b.close for b in bars[:seed_bars]],
            bars[seed_bars - 1].date,
        )
        if symbol in preset_levels:
            engine.set_levels({symbol: preset_levels[symbol]})
            engine.frozen.add(symbol)
        else:
            engine.set_levels({symbol: seed_ranges[-1].low})
        engine.seed_baseline({symbol: bars[seed_bars - 1].close})
        for bar in bars[seed_bars:]:
            moment = datetime(
                bar.date.year, bar.date.month, bar.date.day, 15, 59, tzinfo=ET
            )
            alert = engine.on_tick(symbol, bar.low, moment)
            if alert is not None:
                fired.append(alert)
            engine.roll_daily_bar(symbol, bar.close, bar.date)
    return fired


class FakeSocket:
    """Deterministic scripted tick source for tests and dry runs."""

    def __init__(self, ticks: list):
        self.ticks = list(ticks)

    def run(self, engine: AlertEngine) -> list[Alert]:
        fired = []
        for symbol, price, moment in self.ticks:
            alert = engine.on_tick(symbol, price, moment)
            if alert is not None:
                fired.append(alert)
        return fired
