---
name: analyst
description: Research a stock and record a Hedgeye-style note in notes/stocks. Use when asked to research a ticker, write up a setup, or update notes/stocks.
---

# Analyst Skill — Hedgeye-style stock notes

Records notes in `notes/stocks/<ticker>.md` (lowercase ticker, e.g. `mnst.md`, `grmn.md`).
Source of truth for process: https://app.hedgeye.com/education (pulled 2026-09-28 via real browser)
plus local summary `notes/hedgeye.md`.

## When to use

- User asks "research TICKER", "write up", "make a note", "long/short candidate"
- Updating an existing `notes/stocks/*.md` on new data / earnings / signal hit

## Hedgeye rules (must follow)

From Education sections I–V:

1. **Philosophy: Preserve, Protect, Compound.** Manage risk first. Static allocations fail when regimes change.
   Stack: **GIP Model → Quads → Signals → Position Sizing.**
2. **The Machine:** algos, ETFs, passive flows, vol drive prices. Vol down = models buy, vol up = models sell all at once. Track flows/positioning, front-run don't react.
3. **GIP / Quads:** Growth + Inflation rate-of-change → 4 regimes. Quarterly Quad = climate, Monthly Quad = weather. A Quad 1 month inside Quarterly Quad 4 = tactical rally in risk-off. Intensity matters, not just direction. TAIL/TREND/TRADE read *inside* the Quad.
4. **Risk Range Signals — price, volume, volatility → probable range:**
   - **LRR (low end) = buy/add. TRR (top end) = sell/trim. TREND/TAIL break = exit completely.**
   - **TRADE:** 3 weeks or less — entries/exits. **TREND:** 3 months+ — cycle direction. **TAIL:** 3 years or less — conviction/regime.
   - Ideal buy/add: **Bullish TRADE *and* TREND + higher highs + higher lows + price near LRR.** Typical add **50–100 bps**; **150–200 bps** on bullish breakout above TRR that holds.
   - **Longs require green across durations: TRADE *and* TREND *and* TAIL all pointing up** (↑↑↑ — higher highs + higher lows on each horizon). Any duration pointing down (→ or ↓) = no new long; at best a small starter or wait for the level. Size scales with alignment: full adds only on ↑↑↑, half size on mixed, nothing on ↓.
   - Sell-some (trim): near TRR; TRADE neutral/bearish while TREND bullish; lower highs. Trim 50–100 bps, more when vol spikes.
   - Exit all: TRADE **and** TREND break; lower highs **and** lower lows; or personal stop. **No story, no hope — just math.** "Tickers, not marriage or religion."
   - **VIX buckets:** 9–19 investable (buy dips), 20–29 chop (trade ranges, aggressive longs), 29+ f\*ck bucket (defensive).
   - Quantamental: research builds the case, **nothing owned until Signal confirms timing.**
5. **Position sizing:** preset min/max per asset class (Keith example: US equity 2% start → 6% max). Adds in 50–100 bps steps. No single trade defines outcome. Define your own min/max up front, scale within by Signal.

### mrmkt mapping (from `notes/hedgeye.md` — state the gaps)

- `mrmkt ranges` (15D horizon) ≈ **one TRADE range**. LRR = buy/add, TRR = sell/trim.
- We compute ONE horizon — **no TREND/TAIL durations**. 200SMA prescreen is a crude TREND proxy, not a signal. No VIX-bucket sizing, no position framework, no Quad map.
- Hedgeye-correct usage: only act on BUY where longer trend intact, trim (don't short) at TRR unless thesis says short-into-strength with stop, size by vol regime (see VoV notes).

## Features — read first, write after

Use the `mrmkt` features store (`mrmkt feature` CLI / `mkt.features` scripting accessor) so notes build on stored work instead of recomputing or re-researching.

- **Read before computing.** Check what's already stored for the ticker:
   ```shell
   uv run mrmkt feature list MNST          # all stored rows, oldest first
   uv run mrmkt feature show MNST rr15.low  # latest value for one feature
   ```
   or in a script: `mkt.features.of_symbol(s)` / `mkt.features.latest(s, name)`.
   Reuse scan rows (`rr15.low`, `rr15.high`, `trend.state`, `vol21`, `mom252` — see `user-scripts/log_scan_features.py`)
   and fundamentals rows (`fundamentals.sequelsec.*`) when their date covers your vintage. Only recompute when stale or missing.
- **Write after computing.** Persist every scan feature you compute for the note via
   `mkt.features.create(symbol, "name=value", vintage_bar_date)` — same names as `log_scan_features.py` — so the next note/scan reuses them.
   Analysis scripts are ephemeral: live in `/tmp`, keep the repo clean (moneyman rule).

## Workflow

1. **Regime first.** `mrmkt` index check: SPY vs 63D/200D, % names above SMAs, `signals current`, VIX bucket. Narrow leadership / broken breadth = fewer, smaller, trend-intact only.
2. **Signal.** `mrmkt ranges` + `mrmkt screen` + `signals current`: px vs BUY (LRR) / SELL (TRR), vsBuy/toSell %, trend_points, vol21, VoV%. State vintage date (= latest stored bar).
3. **Tape.** Bottom/rip/pullback, volume climax, wicks, distance to range top/bottom, MA stack. Parabolic into TRR = short/trim-into-strength, not breakdown.
4. **Fundamentals.** Earnings, segments, margins, guidance, split/buyback, comps. Use web/browser research if `technical-only` store lacks it. Cite sources + dates.
5. **Risks / invalidation.** Hard stop level (e.g. daily close above range high), earnings date check, what breaks thesis.
6. **Write the file.** Create or update `notes/stocks/<ticker>.md`. Keep it short, setup ranking not forecast.

## File format — match `grmn.md`

```markdown
# TICKER (Company Name) — long/short/trim candidate, YYYY-MM-DD

## Signal
Risk-range BUY/SELL hit: $px vs buy $LRR (sell $TRR). Scan rank, vintage date.

## Tape
Price action, volume, MAs, position in band, vsBuy/toSell.

## Fundamental backdrop (source + date)
Earnings, segments, margins, guide, corporate actions, comps.

## Risks / invalidation
- Extension risk, stop level, earnings through risk, data gaps.

## Moneyman notes
Vintage = latest stored bar (YYYY-MM-DD). Setup ranking, trim-signal strength + direction, sizing per Hedgeye buckets.
```

Rules for file:
- Filename lowercase: `notes/stocks/mnst.md`. One file per ticker, newest thesis on top or overwrite with dated header — don't append endless logs.
- Numbers come from `mrmkt` commands unless marked as web research with date.
- Always state: vintage, LRR/TRR, vsBuy/toSell, trend (above/below 63D/200D), VoV/vol regime, VIX bucket if known, stop.
- Never present story without signal. If Signal doesn't confirm, write "good holding, not a buy today" and put px trigger on watch list.

## Example commands

```shell
uv run mrmkt screen --tag sp500 --min-price 10 --min-dollar-vol 5000000 --min-bars 300 --max-stale-days 5 --top 400
uv run mrmkt ranges --symbol MNST
uv run mrmkt signals current --strategy buy-red --tag sp500
```

See `notes/stocks/grmn.md` for a conforming short-into-strength example, and `notes/hedgeye.md` for process gaps.
