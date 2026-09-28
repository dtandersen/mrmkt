---
name: trader
description: Turn analyst setups into sized trade requests with stops. Use when asked to buy/sell/trim, size a position, or act on a notes/stocks note.
---

# Trader Skill — sized trade requests from analyst setups

Turns `notes/stocks/<ticker>.md` setups into executable trade requests,
staged and submitted through `mrmkt order` (paper-only, human-approved).
Paper path: `mrmkt order create SYM --buy QTY --price LIM [--stop S]`
defaults to DAY orders (unfilled legs die at close, no orphans); `--tif gtc`
is an explicit escape hatch. House sizing rule (verified against Alpaca):
fractional + stop leg is REJECTED (fractional must be simple/naked) —
so DAY-with-stops means whole shares (~37–59bps at $100k); exact
fractional only works without a stop, which risk rules forbid — stops win. Alpaca holds
the stop as a separate `held` child order until the parent fills —
`order list` does not join parent+child, check both. Output is a request file a human approves; submission
only with explicit human approval, paper account only.

Source of truth for timing/sizing: the analyst skill Hedgeye rules
(`.agents/skills/analyst/SKILL.md`) + local `notes/hedgeye.md`.

## When to use

- User asks "buy/sell/trim TICKER", "size a position", "act on this note"
- User asks "what would you trade here" after a research note
- An analyst session hands off a setup

## Coordination with the analyst

Trader never researches from scratch. It requests the setup, then validates.

**Multi-session (preferred, per `AGENTS.md`): use `pi-intercom`.**

```typescript
intercom({ action: "list" })  // find the analyst session
// Fire-and-forget request:
intercom({ action: "send", to: "analyst", message: "Setup request: MNST long — need fresh note with LRR/TRR, vintage, trend legs, stop. Buying into strength or at LRR?" })
// Blocking when you cannot proceed without it:
intercom({ action: "ask", to: "analyst", message: "MNST: is TRADE+TREND+TAIL green (↑↑↑)? LRR/TRR + vintage? Earnings date? Hard stop?" })
```

- Prefer `send` for notifications ("request logged, no rush"); `ask` only when
  blocked waiting for the setup (10-min default timeout).
- If the analyst replies with a note path, read that file — do not re-research.

**Single session fallback:** invoke the analyst skill directly
("research TICKER per analyst skill"), then continue below once
`notes/stocks/<ticker>.md` exists and is fresh (vintage = latest stored bar).

## Hedgeye execution rules (must enforce)

1. **Signal is the gate.** In Hedgeye mode, a new long needs TRADE, TREND,
   and TAIL all green (↑↑↑); any flat, down, or missing leg means WATCH. If the
   user explicitly selects a registered `mrmkt` strategy instead, follow that
   strategy's documented entry rules and label its horizons/proxies honestly;
   do not claim it proves full Hedgeye ↑↑↑.
2. **Level discipline:** LRR (low end) = buy/add. TRR (top end) = sell/trim,
   never chase. TREND/TAIL break = exit completely. No story, no hope.
3. **Regime first:** check `signals current`, SPY vs 63D/200D, breadth
   (% names above SMAs), VIX bucket (9–19 normal size, 20–29 half size /
   trade ranges, 29+ defensive only). Narrow leadership / broken breadth =
   fewer, smaller, trend-intact only.
4. **Sizing:** preset min/max up front (e.g. 2% start → 6% max US equity).
   Adds in 50–100 bps steps; 150–200 bps only on bullish TRR breakout that
   holds. Never let one trade define the outcome.
5. **Every request has a stop:** hard level (e.g. daily close above range
   high for shorts, below LRR/200D for longs) + next earnings date and source.
   Mark dates as confirmed or estimated. If only estimated, use the earliest
   credible date as a no-hold-through deadline and recheck before it; if no
   credible date is available, use WATCH. No position into a print without a
   fresh signal.

## Pre-submit condition gate

`mrmkt order create` places a resting DAY limit with an attached stop; it does
not wait for a close, higher high, turn, volume confirmation, rejection wick,
or a human checklist. A limit can fill on a touch before any later review.
Therefore:

- Verify every written entry condition **before** submitting. If a condition
  still needs a future bar, close, volume reading, or analyst update, keep the
  request in WATCH and submit nothing.
- After the trigger is confirmed, refresh the note and levels, then decide
  whether a new order is still valid. Do not leave an order live while waiting
  to see whether its prerequisites happen.
- In Hedgeye mode, missing duration blocks submission. In a user-selected
  registered strategy mode, missing model inputs or stale data blocks; document
  any duration proxies, earnings-date certainty, and event checks. A low limit
  price is not a substitute for the selected strategy's signal.

## Stop placement (vol-scaled buffer)

Thesis stops are close-based ("daily close below LRR / above TRR") but the
broker leg is intraday — a daytime poke can stop out a position whose close
would have held. Size the buffer so normal chop cannot trigger it:

- **Buffer ≈ 1 daily sigma beyond the level.** Daily move ≈ vol21 / √252
  (vol21 0.22 → ~1.4%/day; 0.14 → ~0.9%; 0.32 → ~2%). Calm names (~15%
  vol) ≈ 1% under LRR is enough; high-vol names (30%+) need ~2%.
- **Long starters:** 1–2% under LRR. Prefer stops that exit *before* a
  trend-line break where the geometry allows (e.g. a stop sitting just
  above the 63D keeps the trend leg intact for re-entry).
- **Shorts into strength:** place the stop above both entry and TRR by at
  least the greater of ~0.5% and one daily sigma. Never put it at the range
  top or just a tick beyond it: a stop inside half a daily sigma is a scratch
  machine in chop. Reduce size if the wider stop raises planned risk.
- **Pin to structure, not round numbers:** below Friday's low, above the
  range top, clear of the 63D/200D. Never place a stop in air without
  noting gap-through risk (a stop-market child fills through gaps).
- **Scratch stops are a deliberate exception, not a default.** A
  penny-under-entry stop is a designed free look (bounce or scratch) —
  name it as such in the file.
- **Missing numeric stop = no submit.** If the request says only "below
  LRR", compute the vol-scaled buffer at submit, write the number into
  Status, and mark it trader-set.
- **The DAY leg is disaster insurance, not the thesis stop.** The held
  child dies at close; the human's evening review enforces the close-based
  rule (cancel any leg that closed through its level). Cancel cascades:
  `order cancel <parent-id>` kills parent + held child together — to move a
  stop, cancel and resubmit, never amend. Record the canceled IDs + reason
  in the file.

## Deployment goal

The user's target is to deploy $100,000 gradually, aiming for at least $2,500
of aggregate buy-order notional per trading day. Treat this as a pacing target,
not a quota that overrides the signal, condition, stop, or sizing gates. Add
orders across eligible setups only; never force a trade or use margin to meet
the daily target. Track both accepted order notional and filled buy notional:
only fills count as invested capital. DAY orders that expire unfilled do not
advance the goal. If no eligible setup exists, place no order and let the
schedule extend; do not lower the bar to make the daily number. $100,000 / $2,500
is 40 fully filled trading days, before price changes. The current mrmkt account
is paper-only; do not describe paper activity as real-money investing.

## Workflow

1. **Get the setup.** Intercom request or fresh `notes/stocks/<ticker>.md`.
   Reject stale notes (vintage ≠ latest stored bar — confirm with
   `uv run mrmkt prices freshness --tag sp500 --lookback-days 40`).
2. **Validate.** Quote back: px vs LRR/TRR, vsBuy/toSell %, the selected
   strategy's signal inputs (and TRADE/TREND/TAIL when available), vol21 + VoV
   regime, VIX bucket, breadth, and next earnings date/source. Missing or stale
   inputs required by that strategy mean WATCH. If the note says "good holding,
   not a buy today," output a watch trigger.
3. **Size.** Size only an eligible, confirmed setup. Scale by VIX and breadth;
   state % of equity + bps logic and check aggregate open exposure. No size
   rescues an ineligible signal or an unconfirmed condition.
4. **Write the request.** Create `notes/trades/YYYY-MM-DD-<ticker>.md`
   (lowercase ticker). One file per request, never overwrite — new date =
   new file. Keep unconfirmed setups in `notes/trades/` as WATCH; only submit
   after the pre-submit condition gate passes. On broker acceptance, move the
   file to `notes/trades/executed/` (never copy — one file, one place) and
   update its Status.
5. **Notify.** `send` the request path + one-line summary back to the
   analyst session (or print it single-session). Human approves/executes.

## File format — `notes/trades/YYYY-MM-DD-<ticker>.md`

```markdown
# TRADE REQUEST: TICKER long/short/trim — YYYY-MM-DD

## Setup (from analyst note YYYY-MM-DD, vintage YYYY-MM-DD)

Px $x vs LRR $l / TRR $h (vsBuy +a% / toSell +b%). Durations: TRADE↑ TREND↓ TAIL↑.
Regime: SPY above/below 63D/200D, breadth n%, VIX bucket.

## Action

Buy/add N bps @ limit $x (or: trim N bps / exit all / watch-trigger $x).
Sizing logic: alignment + VIX + breadth in one line.

## Invalidation / stop

Hard stop: daily close [above/below] $s. Earnings YYYY-MM-DD — no hold-through without signal.

## Status

REQUESTED — awaiting human approval. (analyst: <session-or-note-path>)
```

Rules:
- Numbers come from `mrmkt ranges` / `signals current` / the analyst note;
  mark anything else as web research with date.
- Do not submit a new long unless TRADE, TREND, and TAIL are all ↑. For any
  flat, down, or missing leg, write the watch trigger and say why.
- Entry conditions requiring future confirmation must be satisfied before
  order submission; never leave a resting order live to await that confirmation.
- Confirm and record the next earnings date before submission. If unknown, use
  WATCH.
- Never claim an order was placed, filled, or sent to Alpaca unless `mrmkt order`
  output confirms it (accepted + order ID). Paper only, never live.

## Lifecycle (where the file lives)

- `notes/trades/` — not yet sent: REQUESTED (awaiting human),
  STAGED (approved, awaiting conditions/freshness), WATCH (no submit).
- `notes/trades/executed/` — the paper broker accepted the order
  (accepted output + ID recorded in the file). Move the file on submit.
- Status inside executed/: LIVE (working), FILLED (record fill px/qty),
  CANCELED / EXPIRED / REJECTED (record why + broker status).
- Evening reconcile: `mrmkt order list --status all` + `mrmkt position list`
  vs every file in executed/; dead DAY legs get their outcome recorded —
  never delete the file.

## Plain English (house rule — Orwell applies)

Request files are read by a human under time pressure. Short words,
active voice, no jargon where a plain word exists. Numbers and levels
stay exact; the words around them go plain. Backtest stats do not
belong in trade files.

Test: a smart friend with no trading background must grasp the action,
the price, the size, and the exit on first read. Exempt, always:
TRADE / TREND / TAIL — the three durations (weeks / months / years),
up, flat, or down. They are the desk's shared language; use them freely.

## Example commands

```shell
uv run mrmkt ranges --symbol MNST
uv run mrmkt signals current --strategy buy-red --tag sp500
uv run mrmkt prices freshness --tag sp500 --lookback-days 40
```

## Trade request template

Single template — the Setup/Action/Invalidation/Status spine above is
mandatory (levels, durations, sizing, stops, order IDs); the thesis
sections below it are mandatory context (why, edge, risk). One file
per request, never overwrite — new date = new file.

```markdown
# TRADE REQUEST: TICKER long/short/trim — YYYY-MM-DD

## Setup (from analyst note YYYY-MM-DD, vintage YYYY-MM-DD)

Px $x vs LRR $l / TRR $h (vsBuy +a% / toSell +b%). Durations: TRADE↑ TREND↓ TAIL↑.
Regime: SPY above/below 63D/200D, breadth n%, VIX bucket.

## Thesis

Why this setup now — signal + level + tape in 3 lines. What is the edge?

## Pros / Cons

For: reasons to take it (edge, upside, regime fit). Against: risks,
what voids it, what you are explicitly accepting (e.g. blind touch-fill).

## Fundamentals (analyst note + date)

Earnings, margins, guidance, corporate actions; earnings date + hold-through rule.

## Action

Buy/add N bps @ limit $x (or: trim N bps / exit all / watch-trigger $x).
Sizing logic: alignment + VIX + breadth in one line.
Order: mrmkt order create … --tif day (default) + --stop S; record accepted
order ID + held stop-child ID here on submit. Unfilled DAY legs die at close.
Conditions: freshness re-check (>1% LRR restatement = cancel), plus any
note-specific void terms (e.g. turn checklist, gated vintage).

## Invalidation / stop

Hard stop: daily close [above/below] $s. Earnings YYYY-MM-DD — no hold-through without signal.

## Status

STAGED / REQUESTED (awaiting human approval) / SUBMITTED (ids) / FILLED /
CANCELED (reason). (analyst: <session-or-note-path>)
```
