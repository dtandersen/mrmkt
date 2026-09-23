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
```

This command uses the local, git-ignored `alpaca.yaml` and `dbschema.yml` files.
The BDD tests use an in-memory repository and do not call Alpaca or PostgreSQL.

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