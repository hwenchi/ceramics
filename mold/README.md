# mold

A fixed, persistent docker-compose deployment: shared dev shell
(`ceramic`) + postgres + Keycloak + FastAPI + Angular + Caddy, one
instance per VM. See `mold/claude.md` for what the agent is told.

## DNS

Point these at the VM's IP, all A records:
`$DOMAIN`, `api.$DOMAIN`, `kiln.$DOMAIN`, `clay.$DOMAIN`, `bat.$DOMAIN`,
`$AUTH_HOST` (conventionally `auth.$DOMAIN`).

## Deploy

1. `cp .env.example .env` and fill it in.
2. `./setup.sh user@host` — installs docker if missing, creates the
   `/srv/mold/{workspace,data,deploy}` roots, syncs this directory over,
   scaffolds the workspace on first run only, brings the stack up.

Re-running `setup.sh` is safe — the docker install and workspace scaffold
steps are both skipped once already done; everything else just re-syncs.
