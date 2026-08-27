You're running in the `ceramic` container of a persistent, shared
deployment. Multiple people may be connected to this same terminal at
once — ttyd shares one tmux session across every viewer. Nothing you do
here is private or disposable.

The app runs in its own containers, already started — you're editing its
source, not launching it:
- Backend: FastAPI in /workspace/backend, `uv run uvicorn --reload`.
- Frontend: Angular in /workspace/frontend, `ng serve`.
- Postgres: reachable at `postgres:5432`, database `app`. No psql client
  is installed in this container — do DB work through the app's own
  code/migrations.
- Auth: Keycloak, realm `app`. Client IDs are already configured.

This container has no Docker access, except three commands for the fixed
set of containers:
- `restart-service <fastapi-dev|angular-dev>` — e.g. after adding a
  dependency.
- `service-logs <name>` — any container.
- `service-status` — state of every container.

Never use the Artifact tool or other publishing features.
