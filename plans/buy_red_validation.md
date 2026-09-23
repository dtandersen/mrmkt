# Buy-red validation plan

Working hypothesis: the recorded backtest suggests modest trade-level
edge (+0.40–0.54% expectancy, PF 1.15–1.23), and the VoV variant improves
win rate/expectancy. Neither the edge nor the reported portfolio metrics
are validated yet: the test window starts around late 2022, and the current
runner has accounting/fill-model concerns that must be resolved first.
The recorded results also trail buy-and-hold on CAGR and Sharpe; recompute
those comparisons with consistent portfolio accounting before drawing a
conclusion.

These three tests, in order, decide whether it graduates from entry
timing tool to real strategy component.

## Design principle: freeze BuyRed, grow new classes
`BuyRedStrategy` (both variants) is frozen — no rule changes, ever.
Every new idea becomes a new `Strategy` subclass reusing the
`StrategyRunner` (e.g. `NaiveDipStrategy`, `RegimeGatedStrategy`).
Comparisons run head-to-head through the same runner, costs, and
windows, so results stay attributable to the rules, not the plumbing.

## 0. Backtest correctness gate (before accepting performance claims)
Resolve these against the current implementation and rerun the baseline
before comparing strategy variants.

### Implemented in the current worktree; add regression coverage
- `BuyRedStrategy.generate` now passes configured `vol_period` and
  `vov_lookback` to `vov_percentile`, and `trail_lookback` is separate from
  the VoV ranking lookback.
- `StrategyRunner` now forwards fees to `aggregate_trades`, and portfolio
  returns include zero-return cash days for calendar-based annualization.
- These are partial fixes, not a completed validation gate: retain tests that
  demonstrate the intended behavior, and address the remaining issues below.

### Still open
- **Separate commissions from execution friction.** Alpaca charges $0
  commission for these trades, so a zero commission default is appropriate.
  But that does not make execution friction zero: spreads, slippage, market
  impact, and any applicable regulatory/pass-through charges still matter.
  Keep these costs explicit and configurable (for example, an all-in
  0/5/10bps-per-side sensitivity), and label the parameter accurately rather
  than calling it commission. The CLI currently does not expose a cost option.
  Add a regression test proving modeled costs reduce net expectancy and
  portfolio returns exactly once; do not restore 10bps as an assumed Alpaca
  commission.
- **Align active-position accounting.** For closed trades, daily marks include
  the exit date (`g0 + 1` through `g1`), while `open_count` currently excludes
  `g1`. On dates where a position exits while others remain open, the return
  and exit cost can be divided by too few positions. Make the holding/counting
  interval consistent with the daily-return interval; test overlapping trades
  with one exit and another position continuing.
- **Use executable fills and stops.** Entries/exits are triggered by same-day
  low/high touches, but the simulator fills signals at the close. Choose a
  coherent model: use levels known as of the prior close and simulate limit
  fills (including gaps), or execute close-derived signals at the next bar.
  The current fill call receives close only, so its stop is not an intraday
  OHLC stop model. Include realistic slippage and stop-gap behavior.
- **Make `size_pct` real.** The current equal-weight overlay fully normalizes
  across open positions; `size_pct` does not correspond to actual portfolio
  weights/cash usage. Implement consistent position weights, cash constraints,
  and the `max_positions` cap, or clearly define and remove the unused sizing
  setting from reported portfolio claims.
- **Reconcile the tested rules with source and notes.** The recorded notes
  describe an entry-day TRR target and a 63-day time stop. Current exits use a
  contemporaneous rolling sell range, and the runner does not appear to have
  a 63-day time stop. Identify which code produced the recorded results and
  align the experiment description before comparing variants.
- **Keep benchmarks comparable.** Compare strategy and benchmark over
  identical dates, universe, weighting, costs, and cash/exposure assumptions;
  report exposure alongside CAGR and Sharpe.

**Gate:** do not use existing CAGR, Sharpe, or net-expectancy figures to pass
or fail the strategy until the open items are resolved and the baseline is
recomputed. Keep the signal rules frozen while fixing/evaluating the engine;
put any rule changes in separate strategy classes.

## 1. Bear-market window (regime robustness)
**Question:** does expectancy survive a real drawdown regime?
**Work:** backfill prices through 2022 (ideally to 2020 for the COVID
crash), re-run buy-red A/B on a point-in-time universe including delisted
names where possible. Evaluate bear and bull subperiods separately.
**Pass bar:** expectancy stays positive; drawdown stays within 1.2x of
universe BH drawdown. If it becomes a knife-catcher (negative
expectancy, deep DD), buy-red is bull-regime-only and needs test 3.

## 2. Naive baseline (complexity check)
**Question:** does 200 lines of VoV/risk-range machinery beat dumb rules?
**Work:** implement `NaiveDipStrategy` (buy every 5% dip from trailing
high, sell every 5% rip / fixed holding period) in
`src/mrmkt/backtest/strategy/`; run head-to-head on the same
point-in-time universe, window, fills, and costs.
**Pass bar:** buy-red beats naive on expectancy AND profit factor. If
not, simplify the system to the naive rules plus the VoV filter only.

## 3. Regime filter (bull-market weapon)
**Question:** does gating longs on market regime fix the whipsaw leak
(59% of exits are 63D-SMA whipsaws)?
**Work:** implement a NEW `RegimeGatedStrategy` class (never modify
`BuyRedStrategy`) — a wrapper holding any inner strategy whose entries
are ANDed with a market gate: only take longs when SPY (or the
equal-weight universe mean) is above its 200D SMA. Requires SPY
history (already backfilled) plumbed as an extra input frame.
**Pass bar:** fewer trades, higher win rate, expectancy improves vs
unfiltered on the same window; combined with test 1, drawdown drops
materially in bear regimes.

## 4. Follow-up strategy candidates (new classes; keep BuyRed frozen)
Only begin these comparisons after the correctness gate. Each candidate is a
separate `Strategy` subclass and must use the same point-in-time universe,
portfolio accounting, fills, costs, benchmark dates, and holdout window.

### A. Trend + relative-strength pullback (preferred first experiment)
**Hypothesis:** pullbacks are more attractive in stocks already leading a
bullish market; a recovery trigger may avoid buying a dip that is still
accelerating downward.

**Candidate rules to test, not assumed-optimal parameters:**
- Market gate: SPY above its 200D SMA, optionally requiring the SMA to be
  rising. Apply the same gate to all relevant comparisons.
- Stock eligibility: price above its rising 200D SMA and in a high
  cross-sectional rank (for example, top third) of 6–12 month momentum,
  excluding the most recent month. Use point-in-time membership and avoid
  using future constituents.
- Entry: pull back toward a 20D average or volatility-adjusted band, then
  require a recovery condition (for example, close back above the prior
  day's high or a short-term average). Define the level from information
  available before the fill; use next-bar execution or a documented limit
  fill model.
- Exit: compare the current full exit at the rolling range top with a
  slower trend exit and a partial-profit/runner variant. Candidate risk
  controls include an initial ATR-based stop, taking partial profit at a
  fixed multiple of initial risk, and trailing the remainder by ATR or a
  slower moving average. Treat all thresholds as hypotheses and test them
  out of sample.
- Sizing: use a consistent per-position risk budget with name/sector and
  portfolio exposure caps; do not infer portfolio weights from trade returns.

### B. Simple momentum-rotation comparator
Test a monthly or otherwise fixed-schedule rotation into the strongest
eligible stocks/sectors, with a clearly specified cash or defensive regime.
This checks whether relative strength and a broad trend gate explain the
performance without the pullback/risk-range machinery.

**Evaluation:** compare each candidate against BuyRed A/B, the naive dip
baseline, and buy-and-hold using identical execution and portfolio
assumptions. Report net and gross returns, CAGR, Sharpe, max drawdown,
exposure, turnover, expectancy, and profit factor. Use a chronological
holdout and time-blocked uncertainty estimates; do not select rules or
thresholds on the final test period. Prefer improvements in out-of-sample
risk-adjusted portfolio results over a higher win rate alone.

## Standing caveats (apply to all tests)
- Survivorship bias: current constituents only; use point-in-time membership
  and include delisted securities where possible. Current-universe backtests
  can flatter results.
- Trades across symbols/dates are correlated. Report uncertainty with
  date/time-blocked resampling (not an independent-trade bootstrap), and keep
  a final chronological holdout untouched during development.
- Alpaca commissions are $0 for these trades; do not conflate that with zero
  trading friction. Explicitly model executable fills, spreads, slippage, stop
  gaps, and any applicable regulatory/pass-through charges. Report sensitivity
  to all-in costs (including zero-cost and nonzero-cost cases). Adjusted OHLC
  prices are only an approximation to total-return and executable-price
  histories.
- Keep DB `double precision`; engine stays float32 + chunked.
