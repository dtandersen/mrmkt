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
uv run mrmkt prices import --provider alpaca AAPL MSFT --from 180d
uv run mrmkt prices import --provider alpaca --all --from 180d
uv run mrmkt prices list AAPL MSFT --from 7d
uv run mrmkt prices import --provider alpaca AAPL --from 2024-01-01 --to 2024-01-31
```

Price imports use daily adjusted bars; `--all` imports symbols from the local
catalog. Relative dates such as `180d` are measured back from today, and an
omitted `--to` defaults to today. Price listing requires explicit symbols and
can optionally filter by date range. The commands use the local, git-ignored
`alpaca.yaml` and `dbschema.yml` files. The BDD tests use in-memory repositories
and a fake clock; they do not call Alpaca or PostgreSQL.

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