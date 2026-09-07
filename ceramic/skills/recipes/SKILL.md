---
name: recipes
description: Use when the user asks what this pod is for, what they can do here, or wants to run/start/switch a demo (jupyter, code editor, vnc desktop, search engine, etc).
---

# What this pod is
A real Linux environment, not limited to the recipes below — install and run whatever the task needs. If asked what's possible here, answer in your own words, conversationally, like you're talking to a person — don't recite this file back at them.

Background facts, not a script to read out — bring one up only if it's actually relevant to what's being asked:
- Hard limits: 2GB memory, 2 CPU cores, 8GB disk. Over memory = OOM kill, not throttling.
- No sensitive data.
- No nested containers/Docker.
- No GPU yet.

# Recipes
`/opt/recipes/` holds pre-built demos, a starting point not a ceiling. See `recipes/README.md` for the list and order, `<slug>/README.md` for what each does.

Start one with `bash /opt/recipes/lib/launch.sh <slug>` — this is the only entrypoint. It stops whatever recipe is currently running, installs the new one (progress goes to `/var/log/console.log`), then starts it on port 8080, the only port reachable from outside the pod. It runs in the foreground — background it (e.g. `nohup ... &`) to keep working.

While it's installing, tell the user they're welcome to hit refresh above and watch it happen live - it's the actual machinery doing its work, so it might look like gibberish right now, but that's normal, and it'll start meaning something the more they see it. Once it's ready, tell them to refresh again to see it.

Each recipe's `install.sh`/`start.sh`/`stop.sh` are implementation details of `launch.sh`. Never call them directly.

New recipes follow the same shape; state (venvs, downloads, pids) goes in `/var/lib/recipes/<slug>/`, not the recipe folder.
