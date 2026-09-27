# Realtime risk-range alerts

Timing information only: triggers are not advice, not orders, and no fill
at a level is guaranteed. Live quotes and stored daily-bar closes differ —
a stored close is history, a live ask is now.

## Commands

```shell
uv run mrmkt ranges AAA --as-of 2026-09-22
uv run mrmkt ranges --tag sp500
uv run mrmkt watch AAA
uv run mrmkt watch AAA --feed sip
uv run mrmkt trigger create dip-watch --symbol CPAY --indicator risk-range --operator crossing-down --frequency once
uv run mrmkt trigger list
uv run mrmkt watch --all-triggers
```

`ranges` prints deterministic CSV (`symbol,as_of,close,range_low,`
`range_high,n_bars` with a `# key=value` header) from stored bars using
the shared `risk_range_series` definition (H=15/V=21/W=0.5/anchor=5,
minimum 30 bars). Bare `watch` streams every enabled stored trigger;
pass symbols to watch ad-hoc symbols instead. `watch` uses the built-in
risk-range levels and regular-session policy.

`watch` subscribes the selected symbols to the live quote source, evaluates
the ask against each configured level for a long entry, and prints each hit
to the console. The displayed ask is not a guaranteed fill price.
Notification sinks and historical dry-run replay are not part of the basic
watch flow yet. Ctrl+C stops the watch cleanly: it prints `Stopped watching.`
and exits 0.

## Stored triggers (`mrmkt triggers`, DB-backed)

Triggers persist in the `trigger` table (run `dbschema -c dbschema.yml` to
apply pending migrations), so a symbol is associated with its alert
configuration and `watch` can monitor a stored set: `trigger create/list/show/delete`, then `watch --trigger 1
--trigger 2` or `watch --all-triggers` (enabled, unexpired only).

Each row: `symbol | indicator | operator | value | frequency | expires_at |
message | enabled`. `value` empty means the computed risk-range buy level
(frozen per trigger only when explicitly set); `message` is a template
with `{symbol}` `{price}` `{level}` `{moment}` `{session}` placeholders
(empty means the default trigger line).

## Trigger semantics

- One alert per touch: a fire needs an observed above-level ask followed
  by an at-or-below ask (transition-only). The first quote per symbol
  only establishes a baseline and never fires — except when seeded from
  the latest stored close: prior close above the level plus a first
  regular-session quote with an ask at/below fires once as an opening-gap cross,
  while a prior close already below needs a later re-cross.
- Re-arm: an above-level ask re-arms in any session; repeated below asks do
  not re-fire.
- Operators: `crossing-down` (default) and `crossing-up` fire on observed
  transitions; `greater-than` / `less-than` fire while the price holds
  beyond the level. Frequencies: `once_per_rearm` (default), `once`
  (fires a single time, then auto-disables the stored trigger and never
  re-arms), `every_time` (every in-policy tick while a holding condition
  holds; only meaningful with `greater-than` / `less-than`).
- `expires_at` disables firing after that date (expired quotes are recorded
  as ignored with reason `trigger expired`).
- Arm state is in-memory; restarts reset dedupe.

## Sessions

Moments classify in US Eastern (DST-aware) as `regular` (09:30–16:00),
`pre` (04:00–09:30), `post` (16:00–20:00), or `closed` (otherwise and
weekends). Only regular-session quotes may fire. Pre/post/closed quotes do
not fire; above-level asks can still re-arm a trigger. There is no
exchange-holiday calendar: holidays classify as sessions, the stream
delivers nothing on them, and arming is unaffected.

## Price updates

Levels are computed from stored daily bars when the watch starts and stay
fixed for that run. The live source then streams quotes only, and the ask is
used for long-entry trigger evaluation. Quote timestamps are used for session
classification (receipt clock is a fallback only).

## Data caveats

Levels derive from split/dividend-adjusted stored closes with no
adjustment provenance — gaps can suggest but never prove corporate
actions (see `docs/screener.md` freshness notes).
