#!/usr/bin/env python3
"""Fixed YouTube video, filtered with ffmpeg."""
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VIDEO_URL = "https://www.youtube.com/watch?v=gbO7qQliXT8"
VIDEO_FILTER = "rgbashift=rh=15:bh=-15"   # "rgb shift"
AUDIO_FILTER = "vibrato=f=6:d=0.5"        # "vibrato"

HOST = "0.0.0.0"
PORT = 8080

resolve_lock = threading.Lock()
resolved_urls = None   # (video_url, audio_url), set on first request
procs_lock = threading.Lock()
active_procs = set()   # ffmpeg subprocesses currently streaming to a viewer


def handle_sigterm(signum, frame):
    """Terminate any ffmpeg children before exiting."""
    with procs_lock:
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


def get_resolved_urls():
    """Resolve VIDEO_URL to direct CDN URLs once and reuse them - ffmpeg
    reads straight off the network, no local download. These URLs are
    time-limited, but that's fine for one sitting."""
    global resolved_urls
    if resolved_urls is not None:
        return resolved_urls
    with resolve_lock:
        if resolved_urls is not None:
            return resolved_urls
        out = subprocess.run(
            ["yt-dlp", "--no-playlist", "-f", "worstvideo+worstaudio/worst",
             "-g", "--no-warnings", VIDEO_URL],
            capture_output=True, text=True, check=True, timeout=30,
        )
        lines = [line for line in out.stdout.strip().splitlines() if line]
        resolved_urls = (lines[0], lines[1]) if len(lines) >= 2 else (lines[0], lines[0])
        return resolved_urls


PAGE = b"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Stream Filter</title>
<style>
  html, body { height: 100%; margin: 0; background: #000; }
  video { width: 100%; height: 100%; object-fit: cover; }
</style>
</head>
<body>
<video autoplay muted src="/stream"></video>
<script>
document.body.addEventListener('click', () => {
  document.querySelector('video').muted = false;
}, { once: true });
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(PAGE)))
            self.end_headers()
            self.wfile.write(PAGE)
            return

        if self.path == "/stream":
            try:
                video_url, audio_url = get_resolved_urls()
            except Exception:
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
                ["ffmpeg", "-loglevel", "error", *input_args, *map_args,
                 "-vf", VIDEO_FILTER, "-af", AUDIO_FILTER,
                 "-c:v", "libvpx", "-b:v", "300k", "-deadline", "realtime", "-cpu-used", "5",
                 "-c:a", "libopus", "-b:a", "64k",
                 "-f", "webm", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            with procs_lock:
                active_procs.add(proc)
            try:
                while True:
                    # read1(), not read(): read() blocks trying to fill
                    # the full buffer; read1() returns as soon as ffmpeg
                    # has produced anything, which is what a live stream needs.
                    chunk = proc.stdout.read1(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass  # client navigated away/closed the tab
            finally:
                proc.terminate()
                proc.wait()
                with procs_lock:
                    active_procs.discard(proc)
            return

        self.send_response(404)
        self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()
