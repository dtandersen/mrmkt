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
export MRMKT_TRIGGER_PROVIDER=api
export MRMKT_API_URL=https://mrmkt.example.com
export MRMKT_API_TOKEN=...  # same value as the server's
mrmkt trigger list
mrmkt trigger create dip-watch --symbol CPAY --indicator risk-range
mrmkt trigger show dip-watch
mrmkt trigger delete dip-watch
```

With `MRMKT_TRIGGER_PROVIDER=api`, the composition root asks a
`TriggerProviderFactory` for the `api` backend instead of `postgres`
(extra backends register by name; unknown names fail fast listing
what's available). Commands execute locally and unchanged, and every
other command keeps using the local database. `watch` must run
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
