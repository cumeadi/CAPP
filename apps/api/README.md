# apps/api — CAPP Demo API (App A)

> **This is the DEMO API, not the production service.**
>
> It exists to showcase CAPP's SDK/API capabilities through the demo frontends
> (`apps/web`, `apps/wallet`). It is a thin router facade that imports its real
> logic (blockchain clients, agents, services) from the production app,
> `applications/capp/capp`. It has a throwaway synchronous SQLite database and
> **no test coverage**.

## Where the real product lives

The **production API is App B**: [`applications/capp/capp/`](../../applications/capp/capp).

| | App A — this demo | App B — production |
|---|---|---|
| Entry point | `apps/api/app/main.py` | `applications/capp/capp/main.py` |
| Base path | `/` (bare routes, e.g. `/wallet/send`) | `/api/v1/*` |
| Database | sync SQLAlchemy over SQLite (`capp.db`) | async SQLAlchemy + Postgres + Alembic |
| Auth | dev API-key only | JWT + agent-credential middleware |
| Tests | none | ≥60% coverage floor (`pytest`) |
| Deployed? | **no** — demo only | **yes** — root `Dockerfile`, DigitalOcean `app.yaml` |

## Why it still exists

The `apps/web` and `apps/wallet` demo frontends call App A's bare routes
(`/wallet/send`, `/agents/feed`, `/routing/calculate`, …). App A wires those
routes to App B's shared service layer so the demo can exercise real agents and
chain clients without the production auth/persistence stack.

If a capability shown here becomes a real product requirement, it should be
rebuilt natively in App B under `/api/v1` (async, persisted, tested) — not
promoted from this demo code.

## Running the demo

```bash
# from repo root — starts App A + the web frontend together
./start-capp.sh
```

Do **not** deploy this app. Deployment always targets App B via the root
`Dockerfile` (`CMD ... applications.capp.capp.main:app`).
