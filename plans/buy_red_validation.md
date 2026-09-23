# Buy-red validation plan

Verdict to overturn: the buy-red signal has real trade-level edge
(+0.40–0.54% expectancy, PF 1.15–1.23, VoV filter validated in A/B),
but as a standalone long-only system it captures half the market
(+21.9% vs +42.7% BH, Sharpe 1.08 vs 1.62) and has never seen a bear
market (test window starts Dec 2022).

These three tests, in order, decide whether it graduates from entry
timing tool to real strategy component.

## Design principle: freeze BuyRed, grow new classes
`BuyRedStrategy` (both variants) is frozen — no rule changes, ever.
Every new idea becomes a new `Strategy` subclass reusing the
`StrategyRunner` (e.g. `NaiveDipStrategy`, `RegimeGatedStrategy`).
Comparisons run head-to-head through the same runner, costs, and
windows, so results stay attributable to the rules, not the plumbing.

## 1. Bear-market window (regime robustness)
**Question:** does expectancy survive a real drawdown regime?
**Work:** backfill prices through 2022 (ideally to 2020 for the COVID
crash), re-run buy-red A/B on tickers with full history.
**Pass bar:** expectancy stays positive; drawdown stays within 1.2x of
universe BH drawdown. If it becomes a knife-catcher (negative
expectancy, deep DD), buy-red is bull-regime-only and needs test 3.

## 2. Naive baseline (complexity check)
**Question:** does 200 lines of VoV/risk-range machinery beat dumb rules?
**Work:** implement `NaiveDipStrategy` (buy every 5% dip from trailing
high, sell every 5% rip / fixed holding period) in
`src/mrmkt/backtest/strategy.py`; run head-to-head on the same
universe, window, costs.
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
- Survivorship bias: current constituents only; flatters all CAGRs.
- Close fills, 10bps/side costs, adjusted closes ≈ total return.
- Keep DB `double precision`; engine stays float32 + chunked.
