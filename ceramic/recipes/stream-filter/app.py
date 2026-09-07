#!/usr/bin/env python3
"""YouTube link -> ffmpeg-filtered video+audio, muxed into a live WebM and
played directly in a <video> tag. Stdlib + subprocess only."""
import json
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DEFAULT_URL = "https://www.youtube.com/watch?v=GotlA1KKWoo"

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

state_lock = threading.Lock()
current_display_url = DEFAULT_URL
current_video_url = None   # resolved lazily on first request
current_audio_url = None
current_video_filter = next(iter(VIDEO_FILTERS))
current_audio_filter = next(iter(AUDIO_FILTERS))
active_procs = set()  # ffmpeg subprocesses currently streaming to a viewer


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


def resolve_url(raw: str):
    """Returns (video_url, audio_url) via yt-dlp - two URLs, since current
    YouTube content has no single muxed format."""
    try:
        out = subprocess.run(
            ["yt-dlp", "-f", "worstvideo+worstaudio/worst", "-g", "--no-warnings", raw],
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


def get_state():
    with state_lock:
        return current_video_url, current_audio_url, current_video_filter, current_audio_filter, current_display_url


def set_stream_url(url: str) -> None:
    global current_display_url, current_video_url, current_audio_url
    video_url, audio_url = resolve_url(url)
    with state_lock:
        current_display_url = url
        if video_url:
            current_video_url = video_url
            current_audio_url = audio_url


def set_video_filter(name: str) -> None:
    global current_video_filter
    if name in VIDEO_FILTERS:
        with state_lock:
            current_video_filter = name


def set_audio_filter(name: str) -> None:
    global current_audio_filter
    if name in AUDIO_FILTERS:
        with state_lock:
            current_audio_filter = name


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
</style>
</head>
<body>
<div class="bar">
  <input id="urlbox" type="text" value="{display_url}" placeholder="Paste a YouTube URL...">
  <button onclick="setUrl()">Load</button>
  <select id="vfilter" onchange="setVideoFilter()">{video_options}</select>
  <select id="afilter" onchange="setAudioFilter()">{audio_options}</select>
</div>
<div style="position: relative; flex: 1; min-height: 0;">
  <video id="frame" src="/stream.webm" autoplay muted controls style="width: 100%; height: 100%; object-fit: contain; background: #000;"></video>
  <button id="unmute" onclick="unmute()" style="position: absolute; top: 10px; right: 10px; font-size: 0.85rem; padding: 6px 12px; border: none; border-radius: 4px; background: #2c3e50; color: white; cursor: pointer;">&#128266; Unmute</button>
</div>
<script>
function unmute() {{
  const v = document.getElementById('frame');
  v.muted = false;
  document.getElementById('unmute').style.display = 'none';
}}
function reload() {{
  document.getElementById('frame').src = '/stream.webm?r=' + Date.now();
}}
function setUrl() {{
  const url = document.getElementById('urlbox').value.trim();
  if (!url) return;
  fetch('/set_url?url=' + encodeURIComponent(url)).then(reload);
}}
function setVideoFilter() {{
  fetch('/set_video_filter?name=' + encodeURIComponent(document.getElementById('vfilter').value)).then(reload);
}}
function setAudioFilter() {{
  fetch('/set_audio_filter?name=' + encodeURIComponent(document.getElementById('afilter').value)).then(reload);
}}
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
            video_url, audio_url, vfilter, afilter, display_url = get_state()
            body = PAGE_TEMPLATE.format(
                display_url=display_url,
                video_options=options_html(VIDEO_FILTERS, vfilter),
                audio_options=options_html(AUDIO_FILTERS, afilter),
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/stream.webm":
            video_url, audio_url, vfilter, afilter, _ = get_state()
            if video_url is None:
                # First request: resolve the default URL now.
                set_stream_url(current_display_url)
                video_url, audio_url, vfilter, afilter, _ = get_state()
            if video_url is None:
                self.send_response(503)
                self.end_headers()
                return

            if video_url == audio_url:
                input_args = ["-i", video_url]
                map_args = []
            else:
                input_args = ["-i", video_url, "-i", audio_url]
                map_args = ["-map", "0:v:0", "-map", "1:a:0"]

            self.send_response(200)
            self.send_header("Content-Type", "video/webm")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error",
                 *input_args, *map_args,
                 "-vf", VIDEO_FILTERS[vfilter],
                 "-af", AUDIO_FILTERS[afilter],
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
