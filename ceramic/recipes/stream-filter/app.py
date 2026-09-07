#!/usr/bin/env python3
"""YouTube link -> ffmpeg-filtered video+audio, muxed into a live WebM and
played directly in a <video> tag. Stdlib + subprocess only.

A finite video (has a real duration) is downloaded once into a local file
(DATA_DIR); every viewer's stream and every seek is served from that file.
Two things need this:
  - Seeking directly against YouTube's served URLs is unreliable - CDN
    manifests for some videos resolve to HLS, and input-seeking (-ss before
    -i) on those can silently fail for the video track while the audio
    track keeps working, which looks like "the picture disappeared". A
    local file has no such issue: ffmpeg seeks it precisely and instantly.
  - A single shared playback clock (position/playing/updated_at below) is
    what makes every viewer - and a refreshed tab - see the same moment in
    the video, rather than each connection tracking its own private offset.

An actual live stream (a channel broadcasting right now, no fixed end) has
no "whole file" to download - that's not a corner case here, it's the
recipe's default video. Those are detected up front and handled the old
way instead: proxy the two live CDN URLs straight through per viewer, with
no local file and no seeking, the same way a live TV feed has no scrubber.
"""
import glob
import json
import os
import signal
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DEFAULT_URL = "https://www.youtube.com/watch?v=GotlA1KKWoo"
DATA_DIR = "/var/lib/recipes/stream-filter"
LOCAL_VIDEO = os.path.join(DATA_DIR, "current.mkv")

VIDEO_FILTERS = {
    "rgb shift": "rgbashift=rh=15:bh=-15",
    "edgedetect": "edgedetect",
    "negate": "negate",
    "hue rotate": "hue=h=90",
    "contrast boost": "eq=contrast=2:brightness=0.1",
    "pixelize": "pixelize=w=16:h=16",
    "motion trails": "tmix=frames=8",
    "vignette": "vignette",
    "noise": "noise=alls=30:allf=t",
}

AUDIO_FILTERS = {
    "echo": "aecho=0.8:0.9:1000:0.3",
    "slow/deep": "atempo=0.8",
    "fast/chipmunk": "atempo=1.5",
    "vibrato": "vibrato=f=6:d=0.5",
    "tremolo": "tremolo=f=10:d=0.8",
    "chorus": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3",
    "flanger": "flanger",
    "telephone": "highpass=f=1000,lowpass=f=3000",
    "bass boost": "bass=g=15",
}

HOST = "0.0.0.0"
PORT = 8080

os.makedirs(DATA_DIR, exist_ok=True)

state_lock = threading.Lock()
current_display_url = DEFAULT_URL
current_is_live = None      # None until first resolved; True/False after
current_local_path = None   # set for a finite (downloaded) video
current_video_url = None    # set for a live source instead
current_audio_url = None
current_duration = None     # seconds, if known (never known for a live source)
current_video_filter = next(iter(VIDEO_FILTERS))
current_audio_filter = next(iter(AUDIO_FILTERS))
current_position = 0.0      # the shared playhead, in source-video seconds
current_playing = True
current_updated_at = time.monotonic()   # wall-clock time current_position was last set
current_generation = 0      # bumped on any change a viewer should reload for
active_procs = set()        # ffmpeg subprocesses currently streaming to a viewer


def handle_sigterm(signum, frame):
    """A process should clean up what it started. Terminate any ffmpeg
    children we spawned before exiting, rather than leaving them for
    whoever stopped us to discover and guess at from outside."""
    with state_lock:
        procs = list(active_procs)
    for proc in procs:
        proc.terminate()
    for proc in procs:
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_sigterm)


def probe_live(raw: str) -> bool:
    """True if `raw` is a channel broadcasting right now (no fixed end),
    as opposed to an on-demand video - including a past broadcast's VOD
    replay, which yt-dlp reports as not live and does have a duration."""
    try:
        out = subprocess.run(
            ["yt-dlp", "--no-playlist", "--no-warnings", "--skip-download",
             "--print", "is_live", raw],
            capture_output=True, text=True, timeout=20,
        )
        lines = out.stdout.strip().splitlines()
        return bool(lines) and lines[0].strip().lower() == "true"
    except Exception:
        return False


def resolve_live_urls(raw: str):
    """Returns (video_url, audio_url) via yt-dlp - direct CDN URLs to proxy
    per viewer, since a live source can't be downloaded to a whole file."""
    try:
        out = subprocess.run(
            ["yt-dlp", "--no-playlist", "-f", "worstvideo+worstaudio/worst",
             "-g", "--no-warnings", raw],
            capture_output=True, text=True, timeout=30,
        )
        lines = [line for line in out.stdout.strip().splitlines() if line]
        if len(lines) >= 2:
            return lines[0], lines[1]
        if len(lines) == 1:
            return lines[0], lines[0]
    except Exception:
        pass
    return None, None


def download_video(raw: str):
    """Fetch the lowest-quality muxed copy of `raw` into LOCAL_VIDEO.
    Returns (path, duration_seconds) or (None, None) on failure."""
    for f in glob.glob(os.path.join(DATA_DIR, "current.*")):
        try:
            os.remove(f)
        except OSError:
            pass
    try:
        result = subprocess.run(
            ["yt-dlp", "--no-playlist", "-f", "worstvideo+worstaudio/worst",
             "--merge-output-format", "mkv",
             "-o", LOCAL_VIDEO, "--no-warnings", raw],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0 or not os.path.exists(LOCAL_VIDEO):
            return None, None
    except Exception:
        return None, None

    duration = None
    try:
        dout = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", LOCAL_VIDEO],
            capture_output=True, text=True, timeout=15,
        )
        duration = float(dout.stdout.strip())
    except Exception:
        pass
    return LOCAL_VIDEO, duration


def compute_elapsed(position, playing, updated_at, duration):
    elapsed = position + (time.monotonic() - updated_at) if playing else position
    if duration:
        elapsed = min(elapsed, duration)
    return max(0.0, elapsed)


def get_state():
    with state_lock:
        elapsed = 0.0 if current_is_live else compute_elapsed(
            current_position, current_playing, current_updated_at, current_duration)
        return {
            "is_live": current_is_live,
            "local_path": current_local_path,
            "video_url": current_video_url,
            "audio_url": current_audio_url,
            "display_url": current_display_url,
            "duration": current_duration,
            "vfilter": current_video_filter,
            "afilter": current_audio_filter,
            "playing": current_playing,
            "elapsed": elapsed,
            "generation": current_generation,
        }


def set_stream_url(url: str) -> None:
    global current_display_url, current_is_live, current_local_path
    global current_video_url, current_audio_url, current_duration
    global current_position, current_playing, current_updated_at, current_generation

    is_live = probe_live(url)
    if is_live:
        video_url, audio_url = resolve_live_urls(url)
        ok = video_url is not None
    else:
        path, duration = download_video(url)
        ok = path is not None

    with state_lock:
        current_display_url = url
        if ok:
            current_is_live = is_live
            if is_live:
                current_video_url, current_audio_url = video_url, audio_url
                current_local_path = None
                current_duration = None
            else:
                current_local_path = path
                current_duration = duration
                current_video_url = current_audio_url = None
            current_position = 0.0
            current_playing = True
            current_updated_at = time.monotonic()
            current_generation += 1


def set_video_filter(name: str) -> None:
    global current_video_filter, current_generation
    if name in VIDEO_FILTERS:
        with state_lock:
            current_video_filter = name
            current_generation += 1


def set_audio_filter(name: str) -> None:
    global current_audio_filter, current_generation
    if name in AUDIO_FILTERS:
        with state_lock:
            current_audio_filter = name
            current_generation += 1


def seek_to(t: float) -> None:
    """No-op on a live source: there's no recording to jump around in,
    same as a live TV broadcast."""
    global current_position, current_updated_at, current_generation
    with state_lock:
        if current_is_live:
            return
        target = max(0.0, t)
        if current_duration:
            target = min(target, current_duration)
        current_position = target
        current_updated_at = time.monotonic()
        current_generation += 1


def toggle_play() -> None:
    global current_playing, current_position, current_updated_at, current_generation
    with state_lock:
        if current_is_live:
            return
        if current_playing:
            current_position = compute_elapsed(current_position, current_playing,
                                                 current_updated_at, current_duration)
            current_playing = False
        else:
            current_playing = True
            current_updated_at = time.monotonic()
        current_generation += 1


def options_html(options: dict, selected: str) -> str:
    return "\n".join(
        f'<option value="{name}"{" selected" if name == selected else ""}>{name}</option>'
        for name in options
    )


PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Stream Filter</title>
<style>
  html, body {{ height: 100%; }}
  body {{ margin: 0; background: #000; display: flex; flex-direction: column; }}
  .bar {{ display: flex; gap: 6px; padding: 6px; background: #111; font-family: -apple-system, sans-serif; }}
  .bar input {{ flex: 1; min-width: 0; font-size: 0.75rem; padding: 4px 6px; background: #1a1a1a; border: 1px solid #333; color: #eee; border-radius: 3px; }}
  .bar select, .bar button {{ font-size: 0.75rem; padding: 4px 8px; border: 1px solid #333; border-radius: 3px; }}
  .bar select {{ background: #1a1a1a; color: #eee; }}
  .bar button {{ border: none; background: #2c3e50; color: white; cursor: pointer; }}
  .playbar {{ display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: #111; font-family: -apple-system, sans-serif; }}
  .playbar button {{ border: none; background: #2c3e50; color: white; cursor: pointer; border-radius: 3px; padding: 4px 10px; font-size: 0.85rem; }}
  .playbar input[type=range] {{ flex: 1; }}
  .playbar span {{ color: #aaa; font-size: 0.75rem; min-width: 5.5em; text-align: right; }}
  .loading {{ position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
              background: rgba(0,0,0,0.75); color: #eee; font-family: -apple-system, sans-serif;
              font-size: 0.9rem; }}
  /* Same specificity as the browser's own [hidden] rule (display: none) -
     without this, author-origin styles win the tie and "hidden" is
     silently ignored, leaving this overlay visible all the time. */
  .loading[hidden] {{ display: none; }}
</style>
</head>
<body>
<div class="bar">
  <input id="urlbox" type="text" value="{display_url}" placeholder="Paste a YouTube URL...">
  <button id="loadbtn" onclick="setUrl()">Load</button>
  <select id="vfilter" onchange="setVideoFilter()">{video_options}</select>
  <select id="afilter" onchange="setAudioFilter()">{audio_options}</select>
</div>
<div style="position: relative; flex: 1; min-height: 0;">
  <video id="frame" src="/stream.webm" autoplay muted style="width: 100%; height: 100%; object-fit: contain; background: #000;"></video>
  <button id="unmute" onclick="unmute()" style="position: absolute; top: 10px; right: 10px; font-size: 0.85rem; padding: 6px 12px; border: none; border-radius: 4px; background: #2c3e50; color: white; cursor: pointer;">&#128266; Unmute</button>
  <div id="loading" class="loading" hidden>Loading new video&hellip;</div>
</div>
<div class="playbar">
  <button id="playbtn" onclick="togglePlay()">&#9616;&#9616;</button>
  <input id="seek" type="range" min="0" max="{duration_max}" step="1" value="{elapsed}" {seek_disabled}>
  <span id="timelabel">--:-- / {duration_label}</span>
</div>
<script>
const DURATION = {duration_json};
let seeking = false;      // true while the user is dragging the slider
let loadedGeneration = {generation};

function fmt(s) {{
  if (s == null || !isFinite(s)) return '--:--';
  s = Math.max(0, Math.floor(s));
  const m = Math.floor(s / 60), sec = s % 60;
  return m + ':' + String(sec).padStart(2, '0');
}}
function unmute() {{
  const v = document.getElementById('frame');
  v.muted = false;
  document.getElementById('unmute').style.display = 'none';
}}
function togglePlay() {{
  fetch('/toggle_play').then(refreshFromServer);
}}
function reload() {{
  // Always joins wherever the shared playhead currently is - the server
  // computes the position, the client never tracks its own offset.
  const v = document.getElementById('frame');
  v.src = '/stream.webm?r=' + Date.now();
  v.play().catch(() => {{}});
}}
function setUrl() {{
  const url = document.getElementById('urlbox').value.trim();
  if (!url) return;
  const v = document.getElementById('frame');
  // Stop the current stream right away rather than leaving the old video
  // playing (or a stalled connection open) while the new one resolves,
  // which can take a few seconds (a live source) or longer (a download).
  v.pause();
  v.removeAttribute('src');
  v.load();
  document.getElementById('loadbtn').disabled = true;
  const loading = document.getElementById('loading');
  loading.textContent = 'Loading new video…';
  loading.hidden = false;
  fetch('/set_url?url=' + encodeURIComponent(url))
    .then(() => location.reload())
    .catch(() => {{
      loading.textContent = 'Failed to load that URL — try again';
      document.getElementById('loadbtn').disabled = false;
    }});
}}
function setVideoFilter() {{
  fetch('/set_video_filter?name=' + encodeURIComponent(document.getElementById('vfilter').value))
    .then(refreshFromServer);
}}
function setAudioFilter() {{
  fetch('/set_audio_filter?name=' + encodeURIComponent(document.getElementById('afilter').value))
    .then(refreshFromServer);
}}

const seekEl = document.getElementById('seek');
const playBtn = document.getElementById('playbtn');
const timeLabel = document.getElementById('timelabel');

seekEl.addEventListener('input', () => {{
  seeking = true;
  timeLabel.textContent = fmt(Number(seekEl.value)) + ' / ' + fmt(DURATION);
}});
seekEl.addEventListener('change', () => {{
  fetch('/seek?t=' + Number(seekEl.value)).then(() => {{ seeking = false; refreshFromServer(); }});
}});

// Polling, not push: every viewer (and a refreshed tab) asks the server
// what the shared state is and reloads its stream whenever it's changed
// out from under it - by this tab or by another one.
function refreshFromServer() {{
  fetch('/state').then(r => r.json()).then(st => {{
    playBtn.innerHTML = st.playing ? '&#9616;&#9616;' : '&#9654;';
    if (!seeking) {{
      seekEl.value = st.elapsed;
      timeLabel.textContent = fmt(st.elapsed) + ' / ' + fmt(DURATION);
    }}
    if (st.generation !== loadedGeneration) {{
      loadedGeneration = st.generation;
      reload();
    }}
  }});
}}
setInterval(refreshFromServer, 1500);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/":
            st = get_state()
            duration = st["duration"]
            body = PAGE_TEMPLATE.format(
                display_url=st["display_url"],
                video_options=options_html(VIDEO_FILTERS, st["vfilter"]),
                audio_options=options_html(AUDIO_FILTERS, st["afilter"]),
                duration_json=("null" if duration is None else duration),
                duration_max=(int(duration) if duration else 0),
                duration_label=("--:--" if duration is None else
                                 f"{int(duration) // 60}:{int(duration) % 60:02d}"),
                seek_disabled=("disabled" if not duration else ""),
                elapsed=st["elapsed"],
                generation=st["generation"],
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/state":
            st = get_state()
            body = json.dumps({
                "display_url": st["display_url"],
                "duration": st["duration"],
                "vfilter": st["vfilter"],
                "afilter": st["afilter"],
                "playing": st["playing"],
                "elapsed": st["elapsed"],
                "generation": st["generation"],
            }).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/stream.webm":
            st = get_state()
            if st["is_live"] is None:
                # First request: resolve the default URL now.
                set_stream_url(current_display_url)
                st = get_state()
            if st["is_live"] is None:
                self.send_response(503)
                self.end_headers()
                return

            if st["is_live"]:
                video_url, audio_url = st["video_url"], st["audio_url"]
                if video_url == audio_url:
                    input_args = ["-i", video_url]
                    map_args = []
                else:
                    input_args = ["-i", video_url, "-i", audio_url]
                    map_args = ["-map", "0:v:0", "-map", "1:a:0"]
            else:
                seek_args = ["-ss", str(st["elapsed"])] if st["elapsed"] > 0 else []
                input_args = [*seek_args, "-i", st["local_path"]]
                map_args = []

            self.send_response(200)
            self.send_header("Content-Type", "video/webm")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error",
                 *input_args, *map_args,
                 "-vf", VIDEO_FILTERS[st["vfilter"]],
                 "-af", AUDIO_FILTERS[st["afilter"]],
                 "-c:v", "libvpx", "-b:v", "300k", "-deadline", "realtime", "-cpu-used", "5",
                 "-c:a", "libopus", "-b:a", "64k",
                 "-f", "webm", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            with state_lock:
                active_procs.add(proc)
            try:
                while True:
                    # read1(), not read(): read() on a BufferedReader
                    # blocks trying to fill the full buffer (making
                    # repeated underlying reads), which stalls forwarding
                    # for however long that takes with a slow producer.
                    # read1() returns as soon as any data is available.
                    chunk = proc.stdout.read1(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass  # client navigated away/closed the tab
            finally:
                proc.terminate()
                proc.wait()
                with state_lock:
                    active_procs.discard(proc)

        elif parsed.path == "/set_url":
            url = parse_qs(parsed.query).get("url", [""])[0].strip()
            if url:
                set_stream_url(url)
            self._reply_ok()

        elif parsed.path == "/set_video_filter":
            name = parse_qs(parsed.query).get("name", [""])[0]
            set_video_filter(name)
            self._reply_ok()

        elif parsed.path == "/set_audio_filter":
            name = parse_qs(parsed.query).get("name", [""])[0]
            set_audio_filter(name)
            self._reply_ok()

        elif parsed.path == "/seek":
            try:
                t = float(parse_qs(parsed.query).get("t", ["0"])[0])
            except ValueError:
                t = 0.0
            seek_to(t)
            self._reply_ok()

        elif parsed.path == "/toggle_play":
            toggle_play()
            self._reply_ok()

        else:
            self.send_response(404)
            self.end_headers()

    def _reply_ok(self):
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()
