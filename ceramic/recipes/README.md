# Recipes

Pre-built demos, each runnable with `lib/launch.sh <slug>`. With a new user who has no particular request yet, this is the default guided tour - don't wait to be asked, offer each next step as it comes up, but skip ahead or drop the tour entirely the moment they ask for something specific instead:

1. **`jupyterlab`** - start here.
2. **`stream-filter`** - something fun and visual next: a YouTube video, filtered live with ffmpeg. Show it, let them react. Nothing is editable by the visitor by default. Ask if they want to change it - if yes, its own README explains how (`enable-editing.sh`, then `code-server` to edit `app.py`/`preset.txt` and watch the video change live).
3. **`code-server`** - reached via `stream-filter`'s editing flow above, or on its own.
4. **`remote-desktop`** - once they're done playing with that (bored, or ask "what else"), offer this.

`stream-filter` is the one recipe here written for this project rather than installed as-is, and it exists to be changed - don't wait to be asked, offer to swap the video or audio filter for something else.

The only entrypoints are `lib/launch.sh <slug>` and `lib/stop.sh`. `launch.sh` stops whatever recipe is currently running, runs the new one's install with output going to `/var/log/console.log`, then starts it on port 8080, the only port reachable from outside the pod. `stop.sh` just stops the current recipe, without starting another.

Run `launch.sh` right away rather than just describing the steps - don't make the user ask twice. It returns before the new recipe is actually ready. Tell the visitor: if they want to peek behind the scenes, refresh the panel now and they'll see it setting up; once it's ready, refresh again and they'll see the real thing.

Each recipe folder has its own `install.sh`, `start.sh`, and `stop.sh` - these are implementation details, called by `lib/launch.sh` and `lib/stop.sh`. Never call them directly.

A recipe's folder contains only its code. Its state is stored in `/var/lib/recipes/<slug>/`, not in the recipe's own folder.

Each recipe's `README.md` describes what that recipe does.
