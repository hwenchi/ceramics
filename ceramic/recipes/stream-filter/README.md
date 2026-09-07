# Stream Filter

A fixed YouTube video, filtered live with ffmpeg, served as a raw stream at `/` - no page, no controls. The video autoplays muted - tell the user to click it to unmute.

Nothing is editable by the visitor by default. If they ask what they can change here, `VIDEO_FILTER`/`AUDIO_FILTER` in `app.py` are plain ffmpeg filter expressions; `preset.txt` has one ready-made combination to paste in. Two ways to change them:

- You edit `app.py`/`preset.txt` directly (they're right here, no setup needed), then restart: `bash /opt/recipes/lib/launch.sh stream-filter`.
- The user wants to edit it themselves: run `bash /opt/recipes/stream-filter/enable-editing.sh` (symlinks `app.py` and `preset.txt` into `/workspace/stream-filter`) and `bash /opt/recipes/lib/launch.sh code-server` right away, then tell them to open that folder - see the top-level README for how launching works. Once they say they're done, restart: `bash /opt/recipes/lib/launch.sh stream-filter`.
