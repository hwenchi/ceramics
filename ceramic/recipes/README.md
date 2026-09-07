# Recipes

In suggested order:

1. **`jupyterlab`** — established tool, installed as-is. A notebook environment for writing and running code interactively, mixing code, output, and notes in one document.
2. **`code-server`** — established tool, installed as-is. VS Code, running in the browser.
3. **`remote-desktop`** — established tool, installed as-is. A full graphical Linux desktop (XFCE) with Firefox, viewed like a remote screen.
4. **`gutenberg-search`** — source written for this project, open to modification. Full-text search over a set of public-domain novels, indexed paragraph by paragraph.
5. **`stream-filter`** — source written for this project, open to modification. Live video/audio filters applied to a YouTube stream, switchable without restarting.
6. **`live-captions`** — source written for this project, open to modification. Live speech-to-text captions and audio for a YouTube link, generated with whisper.cpp - audio only, no video. Builds whisper.cpp from source on first install, likely the slowest recipe here - give the user a heads up before starting it.

`gutenberg-search`, `stream-filter`, and `live-captions` exist to be changed. Don't wait to be asked - offer to tweak one, starting with something small and visible, like a color or a label.

The only entrypoints are `lib/launch.sh <slug>` and `lib/stop.sh`. `launch.sh` stops whatever recipe is currently running, runs the new one's install with output going to `/var/log/console.log`, then starts it on port 8080, the only port reachable from outside the pod. `stop.sh` just stops the current recipe, without starting another.

Each recipe folder has its own `install.sh`, `start.sh`, and `stop.sh` - these are implementation details, called by `lib/launch.sh` and `lib/stop.sh`. Never call them directly.

A recipe's folder contains only its code. Its state is stored in `/var/lib/recipes/<slug>/`, not in the recipe's own folder.

Each recipe's `README.md` describes what that recipe does.
