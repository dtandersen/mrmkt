# Realtime risk-range alerts

Timing information only: triggers are not advice, not orders, and no fill
at a level is guaranteed. Live prints and signal-bar closes differ — a
stored daily bar close is history, a live tick is now.

## Commands

```shell
uv run mrmkt ranges AAA --as-of 2026-09-22
uv run mrmkt ranges --tag sp500
uv run mrmkt watch AAA --dry-run
uv run mrmkt watch --tag sp500 --sink stdout --sink file --sink-file alerts.log
uv run mrmkt watch --tag sp500 --sink ntfy --session-policy extended --feed sip
uv run mrmkt triggers add CPAY --operator crossing-down --frequency once
uv run mrmkt triggers list
uv run mrmkt watch --all-triggers --sink ntfy
```

`ranges` prints deterministic CSV (`symbol,as_of,close,range_low,`
`range_high,n_bars` with a `# key=value` header) from stored bars using
the shared `risk_range_series` definition (H=15/V=21/W=0.5/anchor=5,
minimum 30 bars). `watch` needs symbols or `--tag`. Both accept
`--signal` (currently only `risk-range`).

## Stored triggers (`mrmkt triggers`, DB-backed)

Triggers persist in the `trigger` table (run `dbschema -c dbschema.yml` to
apply `migrations/migration9`), so a symbol is associated with its alert
configuration and `watch` can monitor a stored set: `triggers add/list`,
`triggers enable/disable/remove`, then `watch --trigger-id 1
--trigger-id 2` or `watch --all-triggers` (enabled, unexpired only).

Each row: `symbol | signal | operator | value | frequency | expires_at |
message | enabled`. `value` empty means the computed risk-range buy level
(frozen per trigger only when explicitly set); `message` is a template
with `{symbol}` `{price}` `{level}` `{moment}` `{session}` placeholders
(empty means the default trigger line).

## Trigger semantics

- One alert per touch: a fire needs an observed above-level tick followed
  by an at-or-below tick (transition-only). The first tick per symbol
  only establishes a baseline and never fires — except when seeded from
  the latest stored close: prior close above the level plus a first
  regular-session print at/below fires once as an opening-gap cross,
  while a prior close already below needs a later re-cross.
- Re-arm: an above-level tick re-arms in any session; repeats below do
  not re-fire.
- Operators: `crossing-down` (default) and `crossing-up` fire on observed
  transitions; `greater-than` / `less-than` fire while the price holds
  beyond the level. Frequencies: `once_per_rearm` (default), `once`
  (fires a single time, then auto-disables the stored trigger and never
  re-arms), `every_time` (every in-policy tick while a holding condition
  holds; only meaningful with `greater-than` / `less-than`).
- `expires_at` disables firing after that date (expired ticks are recorded
  as ignored with reason `trigger expired`).
- Arm state is in-memory; restarts reset dedupe.
- `--dry-run` replays stored daily lows as regular-session ticks with
  levels/arm state advanced bar by bar (today's low is compared against
  the prior-close level, then today's close rolls for the next session),
  prints `would alert:` lines, and never calls real sinks.

## Sessions (`--session-policy regular|extended`, default `regular`)

Moments classify in US Eastern (DST-aware) as `regular` (09:30–16:00),
`pre` (04:00–09:30), `post` (16:00–20:00), or `closed` (otherwise and
weekends). Under `regular` (default), pre/post/closed ticks never fire
and never disarm; each such below-level tick is recorded with its
session and reason (`--verbose` prints them as `IGNORED`). Under
`extended`, pre/post ticks fire with session-labeled lines. There is no
exchange-holiday calendar: holidays classify as sessions, the stream
delivers nothing on them, and arming is unaffected.

## Daily-bar recompute

The watch subscribes to Alpaca daily bars alongside trades. A strictly
newer bar date rolls its close into history and recomputes the level
(same-day updates are ignored); recomputation re-seeds arm state from
the new close vs the new level. Trade ticks prefer the exchange print
timestamp for session classification (receipt clock is fallback only).

## Sinks (`--sink stdout|file|ntfy`, repeatable)

- `stdout` prints trigger lines; `file` appends them (`--sink-file`).
- `ntfy` POSTs the raw-text trigger line with `Title: {SYM} below
  risk-range buy {level}` and `Priority: 4`. The topic URL comes only
  from the `MRMKT_ALERTS_NTFY_URL` environment variable, falling back
  to the `ntfy` key (legacy misspelling `nfty` also honored) in local
  `config.yaml`; the URL/topic is never echoed, logged, or baked into
  the repo or docs. `config.yaml` is git-ignored.
- Live watching reads Alpaca keys from git-ignored `alpaca.yaml`; the
  default feed is IEX (free-plan SIP is delayed — triggers evaluate on
  the configured feed's prints).

## Data caveats

Levels derive from split/dividend-adjusted stored closes with no
adjustment provenance — gaps can suggest but never prove corporate
actions (see `docs/screener.md` freshness notes).
