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
before comparing strategy variants:

- **Use executable fills.** Entries/exits are triggered by same-day low/high
  touches but the signal simulator fills at the close. Choose a coherent
  model: use levels known as of the prior close and simulate limit fills
  (including gaps), or execute a close-derived signal at the next bar. Include
  realistic slippage and stop-gap behavior.
- **Make `size_pct` real.** Costs flow once through simulation and
  aggregation, and cash days annualize over the full calendar. Still
  open: make `size_pct` correspond to actual portfolio weights/cash
  usage; the current equal-weight overlay fully normalizes across open
  positions.

**Gate:** do not use existing CAGR, Sharpe, or net-expectancy figures to pass
or fail the strategy until these issues are resolved and the baseline is
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

## Standing caveats (apply to all three)
- Survivorship bias: current constituents only; use point-in-time membership
  and include delisted securities where possible. Current-universe backtests
  can flatter results.
- Trades across symbols/dates are correlated. Report uncertainty with
  date/time-blocked resampling (not an independent-trade bootstrap), and keep
  a final chronological holdout untouched during development.
- Explicitly model executable fills, slippage, and stop gaps; costs are
  zero; adjusted OHLC prices are only an approximation to total-return and
  executable-price histories.
- Keep DB `double precision`; engine stays float32 + chunked.
