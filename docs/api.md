# Trigger JSON API

Remote access to the stored trigger catalog. The cluster runs the
watcher against Postgres (`mrmkt watch --all-triggers`) while operators
manage triggers over HTTP — same commands, same validation, no direct
database access from the laptop.

Responses carry DTOs, never entities. Dates are ISO strings
(`expires_at: "2026-12-31"` or `null`).

## Endpoints

| Method | Path                    | Success | Errors            |
| ------ | ----------------------- | ------- | ----------------- |
| GET    | `/api/triggers`         | 200 `[...]` | 500           |
| GET    | `/api/triggers?enabled_only=true` | 200 `[...]` | 500 |
| POST   | `/api/triggers`         | 201 `{...}` | 400 invalid data, 500 |
| DELETE | `/api/triggers/{id}`    | 200 `{...}` (deleted) | 404 unknown id, 500 |
| PATCH  | `/api/triggers/{id}`    | 200 `{...}` | 404 unknown id, 500 |

Error bodies look like `{"errors": ["..."]}` with the same messages
the CLI prints. `POST` runs the CreateTrigger command remotely, so name
generation (`trigger-xxxxx` when omitted) and field validation match the
CLI exactly. `PATCH` takes `{"enabled": true|false}`.

```shell
curl -H "Authorization: Bearer $MRMKT_API_TOKEN" \
  localhost:8000/api/triggers | jq .
curl -X POST -H "Authorization: Bearer $MRMKT_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"dip-watch","symbol":"CPAY","indicator":"risk-range",
       "operator":"crossing-down","frequency":"once"}' \
  localhost:8000/api/triggers | jq .
```

## CLI against the API

```shell
export MRMKT_BACKEND=api
export MRMKT_API_URL=https://mrmkt.example.com
export MRMKT_API_TOKEN=...  # same value as the server's
mrmkt trigger list
mrmkt trigger create dip-watch --symbol CPAY --indicator risk-range
mrmkt trigger show dip-watch
mrmkt trigger delete dip-watch
```

With `MRMKT_BACKEND=api`, the composition root asks a
`MrMktBackendFactory` for the `api` backend instead of `postgres`
(extra backends register by name; unknown names fail fast listing
what's available). The backend IS-A bundle of repository interfaces,
so commands execute locally and unchanged, and every other command
keeps using the local database. `watch` must run
where the database lives (it needs prices, arm state, and the stream),
so keep `watch --all-triggers` on the cluster.

## Server

```shell
export MRMKT_API_TOKEN=...  # leave unset for open local dev only
uv run mrmkt web --host 0.0.0.0 --port 8000
```

`MRMKT_API_TOKEN` is read from the environment on both sides and is
never logged, echoed, or baked into the repo. Without it the API is
open — fine on localhost, not in a cluster.

## Generated Python client

The CLI's HTTP backend uses code generated from `api/openapi.json`
(`src/mrmkt/ext/api_gen/`, via `openapi-python-client`) instead of
hand-written requests: endpoint paths, params, and models derive from
the spec, while status→domain mapping (404→absent, 400→invalid data)
stays in `ApiMrMktBackend` where the domain knowledge lives. The
generated tree is excluded from lint/typecheck; never hand-edit it.

After changing any `/api/*` handler, DTO, or error shape:

```shell
# 1. re-export the spec (exactly as /schema/openapi.json serves it)
# 2. regenerate
uvx openapi-python-client generate --path api/openapi.json \
  --output-path src/mrmkt/ext/api_gen --meta none --overwrite
# 3. run the suite (tests/test_api_spec.py fails if step 1 was skipped)
```

Keep handlers' `operation_id`s stable — they become generated function
names. Document extra statuses with `responses={...}` + a typed DTO
so the generator models errors too.

## Kubernetes sketch

- One Deployment runs `mrmkt web` behind a Service (the API above).
- A second Deployment (or the same image, different args) runs
  `mrmkt watch --all-triggers --sink ntfy`.
- `MRMKT_API_TOKEN`, `alpaca.yaml`, and `dbschema.yml` come from
  Secrets/mounted files; run `dbschema -c dbschema.yml` (includes
  migration13: `trigger.signal` → `trigger.indicator`) before first
  start.
- Only trigger management is remote so far; symbols, prices, and
  trigger sets still need direct database access and follow the same
  DTO + repository pattern when needed.
