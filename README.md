# Mr. Market

Stock market stuff.

## Development

```shell
uv sync
cd tests && uv run python -m unittest discover -s .
```

## CLI

Import active, tradable US-equity symbols from Alpaca into the configured ticker
catalog with:

```shell
uv run mrmkt symbols import --provider alpaca
uv run mrmkt symbols list
uv run mrmkt symbols label AAPL sp500
uv run mrmkt symbols label AAPL,MSFT sp500
uv run mrmkt symbols unlabel AAPL sp500
uv run mrmkt symbols list --tag sp500
uv run mrmkt prices import --provider alpaca --tag sp500 --from 180d
uv run mrmkt prices import --provider alpaca AAPL MSFT --from 180d
uv run mrmkt prices import --provider alpaca --all --from 180d
uv run mrmkt prices list AAPL MSFT --from 7d
uv run mrmkt prices import --provider alpaca AAPL --from 2024-01-01 --to 2024-01-31
uv run mrmkt indicators sma AAPL --period 20 --from 180d
uv run mrmkt indicators volatility AAPL --period 21 --from 180d
uv run mrmkt indicators vol-of-vol AAPL --vol-period 21 --vov-period 21 --from 180d
uv run mrmkt indicators volatility-percentile AAPL --period 21 --lookback 252 --from 180d
uv run mrmkt indicators vol-of-vol-percentile AAPL --vol-period 21 --vov-period 21 --lookback 252 --from 180d
uv run mrmkt indicators risk-range AAPL --horizon 15 --vol-period 21 --width 0.5
uv run mrmkt backtest run --tag sp500 --from 2023-01-01
```

Ticker tags are static labels (for example, `sp500`); comma-separated symbols
can be labeled together, and each label applies to all matching exchange listings. Price imports use daily adjusted bars;
`--all` imports symbols from the local catalog, while `--tag` imports only
symbols with that label. Imports run in batches of 100 symbols with retries and
progress output; batches that keep failing are listed at the end and the command
exits nonzero. Relative dates such as `180d` are measured back from
today, and an omitted `--to` defaults to today. Price listing requires explicit
symbols and can optionally filter by date range. Indicators read stored close prices and
return dated values; prior bars are used as warm-up, but only the requested
range is printed. Volatility is annualized from log returns; volatility of
volatility is the rolling standard deviation of log changes in realized
volatility. Separate percentile commands rank each value against the preceding
`--lookback` observations (default 252), with results on a 0-100 scale. They need
sufficient history before the requested output range. Risk ranges are
volatility-implied buy/sell bands anchored on a fast trailing mean;
`backtest run` evaluates buy-red-in-uptrend signals with the vectorbt
engine (long-only, 2% sizing, 8% stop) over symbols, `--all`, or `--tag`.
The commands use the
local, git-ignored `alpaca.yaml` and `dbschema.yml` files. BDD tests use in-memory
repositories and a fake clock; they do not call Alpaca or PostgreSQL.

## Database

dbschema.yml
```yaml
databases:
    db1:
        engine: postgresql
        host: 127.0.0.1
        port: 5432
        user: postgres
        password: local
        db: mrmkt
        path: migrations
        pre_migration: ''
        post_migration: ''
```

```shell
dbschema -c dbschema.yml
```