You're running in the `ceramic` container of a persistent, shared
deployment. Multiple people may be connected to this same terminal at
once — ttyd shares one tmux session across every viewer. Nothing you do
here is private or disposable.

The app runs in its own containers, already started — you're editing its
source, not launching it. `localhost` here means this container, not
those — reach them by name:
- Backend: FastAPI in /workspace/backend, `curl http://fastapi-dev:8000`.
  Env vars already set: `DATABASE_URL` (psycopg dialect), `OIDC_ISSUER`.
- Frontend: Angular in /workspace/frontend, `curl http://angular-dev:4200`.
- Postgres: reachable at `postgres:5432`, database `app`. No psql client
  here — do DB work through the app's own code/migrations.
- Auth: Keycloak, realm `app`. Two clients, no secret needed for either:
  `web` (frontend) is public, no secret exists; `api` (backend) is
  bearer-only, validates JWTs via the realm's public keys, no secret used.

This container has no Docker access, except three commands for the fixed
set of containers:
- `restart-service <fastapi-dev|angular-dev>` — restarts and reinstalls
  deps; logs checked immediately after may be mid-install, not final.
- `service-logs <name>` — any container.
- `service-status` — state of every container.
- `exec-in <name> '<cmd>'` — run a one-off command there; only
  `fastapi-dev` is allowed for now.

Never use the Artifact tool or other publishing features.
