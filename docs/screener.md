# Screener and signal discovery

Repeatable discovery over the local tagged price catalog. All three commands
read through the repository layer (no ad hoc SQL), print deterministic CSV to
stdout (`# key=value` header lines, then one header row and data rows), and
work against the in-memory repository under BDD tests.

## Commands

```shell
uv run mrmkt screen --tag sp500 --exclude-tag etf --as-of 2026-09-22 --top 20
uv run mrmkt screen --tag sp500 --min-price 10 --min-dollar-vol 1000000 --min-bars 300
uv run mrmkt signals current --tag sp500 --strategy buy-red --benchmark SPY
uv run mrmkt signals current --tag sp500 --strategy trend-pullback --params momentum_top_share=0.5 --benchmark SPY --as-of 2026-09-22
uv run mrmkt signals current --tag etf --benchmark SPY --include-benchmark
uv run mrmkt prices freshness --tag sp500 --lookback-days 365 --stale-after 5 --gap-threshold 0.20
```

`--tag` is repeatable (union); `--exclude-tag` is repeatable (subtracted).
With no `--tag`, all catalog symbols are screened. `scanner.py` at the repo
root is a thin wrapper around the same screen path (`--tag`, `--exclude-tag`,
`--as-of`, `--top`, filters) with no hardcoded symbols.

## As-of and vintage semantics

- Every metric uses only bars on or before `--as-of` (default: latest stored
  bar). `as_of` and `data_vintage` echo in each CSV header.
- `data_vintage` is the latest bar date across the whole screened price
  universe, computed before any `--top` truncation.
- Universe membership is **current, not point-in-time**: tags are current
  assignments and the repository carries no historical tag snapshots.
  `universe_membership_vintage=current` is stamped on every CSV; do not
  treat the historical universe as survivorship-free.
- Fundamentals are unavailable (schema exists, no populated pipeline), so
  `screen --mode` accepts only `technical-only`.

## `screen` ranking

Eligibility first: fixed formation floors (200 bars for trend, 132 for
momentum), then `--min-price` on last close, `--min-dollar-vol` on 63-day
median dollar volume, `--min-bars`, and opt-in `--max-stale-days` on the
calendar-day gap between `as_of` and each symbol's last bar (a Friday bar
screened Monday is 3 days stale, so allow headroom for weekends). Exclusion
reasons are counted separately (`excluded_short_history`,
`excluded_min_price`, `excluded_min_dollar_vol`, `excluded_vol_unavailable`,
`excluded_stale`). Stale names stay listed by default: pair the screen with
`prices freshness` when recency matters.

Score (header echoes the full fixed inputs, not just this formula):

```text
score = 0.4*mom_rank + 0.25*trend_frac + 0.2*pullback_depth_capped + 0.15*(1-vol_rank)
```

`mom_rank`/`vol_rank` are cross-sectional percentile ranks of 126-day return
(skipping 5 days) and 21-day annualized volatility; `trend_frac` is
0/0.5/1 for close above neither/either/both of the 63/200-day SMAs (shared
`sma`/`volatility` indicator definitions); `pullback_depth` is the capped
fractional gap below the 20-day average (cap 0.10). Rows sort by score
descending, symbol ascending.

Columns: `rank,symbol,last_date,last_close,n_bars,sma20,sma63,sma200,`
`dist_sma20,momentum_126_5,vol_21,dollar_vol_med63,trend_points,`
`pullback_depth,score`.

## `signals current` columns and fill convention

Per-symbol status at the signal bar: `entry_signal`, `exit_signal`, or
`neutral`, with `signal_date` and that bar's `close` plus last
entry/exit dates, closes, and days-since. `dist_lo`, `drawdown`,
`vov_pct`, `above_fast`, `above_slow` apply to `buy-red`; `mom_value`,
`mom_rank`, `pullback_dist`, `gate` apply to the `trend-pullback` and
`momentum-rotation` candidates; other cells are empty.

Signal booleans are known only **after** a bar closes. The CSV states the
fill convention explicitly: no fill price is shown or implied. `--benchmark`
(default `SPY`) loads non-tradable gate context and is excluded from the
scored universe unless `--include-benchmark` is passed. The header reports
benchmark status explicitly: `benchmark=SYM (resolved)` when bars loaded,
`benchmark=SYM (missing; strategies use their configured fallback)` when
not, plus `benchmark_tradable=true|false`.

Columns: `symbol,signal_date,close,status,last_entry_date,`
`last_entry_close,last_exit_date,last_exit_close,days_since_entry,`
`days_since_exit,n_bars,dist_lo,drawdown,vov_pct,above_fast,above_slow,`
`mom_value,mom_rank,pullback_dist,gate`.

Backtest trade attribution carries `TradeSummary.symbol` from the fill
records, so per-name performance stays attributable.

## Composite score vs momentum rank

The screen `score` is a four-way composite for leading-pullback
candidates; it is not a momentum sort. A pure cross-sectional momentum
rank (`mom_value`, `mom_rank`, 252/21-style formation skipping 21 days)
is reported per symbol by `signals current --strategy trend-pullback`
(or `momentum-rotation`). Expect the two orderings to differ: the screen
rewards trend plus pullback depth and penalizes volatility, while the
signal rows show raw relative strength.

## `prices freshness` flags (heuristics, not determinations)

Columns: `symbol,n_bars,first_bar,last_bar,staleness_days,expected_bars,`
`missing_bars,flags,flag_details`. Flags: `NO_BARS`, `STALE`,
`GAPS` (missing business-day bars), `OHLC_VIOLATION`, `ZERO_VOLUME`,
`NEGATIVE_VOLUME`, `GAP_JUMP_HEURISTIC` (overnight gaps at/above
`--gap-threshold`, default 20%).

Limitations, also stamped on the CSV: stored bars are split- and
dividend-adjusted (`Adjustment.ALL`) and `StockPrice` carries no adjustment
provenance, so gaps can suggest but never prove corporate actions; missing
bars are measured against plain Mon–Fri business days because there is no
exchange calendar, so market holidays appear as missing.
