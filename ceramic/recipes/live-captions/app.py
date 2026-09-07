#!/usr/bin/env python3
"""YouTube link -> whisper.cpp live captions + audio playback.
Stdlib + subprocess only."""
import json
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

DATA_DIR = "/var/lib/recipes/live-captions"
WHISPER_BIN = f"{DATA_DIR}/whisper.cpp/build/bin/whisper-cli"
WHISPER_MODEL = f"{DATA_DIR}/whisper.cpp/models/ggml-tiny.en-q5_1.bin"
CHUNK_SECONDS = 8

DEFAULT_URL = "https://www.youtube.com/watch?v=GotlA1KKWoo"

HOST = "0.0.0.0"
PORT = 8080

state_lock = threading.Lock()
transcript = deque(maxlen=50)   # list of (timestamp_str, text)
status = {"audio": "starting"}
current_display_url = DEFAULT_URL
current_audio_url = None  # resolved lazily on first use
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

_last_cpu = {"time": None, "usage_usec": None}


def get_system_stats() -> dict:
    """Reads cgroup v2 accounting directly - the same files we've been
    checking by hand all session (memory.current/memory.max, cpu.stat)."""
    stats = {}
    try:
        cur = int(open("/sys/fs/cgroup/memory.current").read().strip())
        limit_raw = open("/sys/fs/cgroup/memory.max").read().strip()
        stats["mem_mb"] = round(cur / 1024 / 1024)
        if limit_raw != "max":
            limit = int(limit_raw)
            stats["mem_limit_mb"] = round(limit / 1024 / 1024)
            stats["mem_pct"] = round(cur / limit * 100, 1)
    except Exception:
        pass
    try:
        cpu_stat = open("/sys/fs/cgroup/cpu.stat").read()
        usage_usec = int(
            next(l for l in cpu_stat.splitlines() if l.startswith("usage_usec")).split()[1]
        )
        now = time.time()
        if _last_cpu["time"] is not None:
            elapsed = now - _last_cpu["time"]
            if elapsed > 0:
                cpu_seconds = (usage_usec - _last_cpu["usage_usec"]) / 1_000_000
                stats["cpu_pct"] = round(cpu_seconds / elapsed * 100, 1)
        _last_cpu["time"] = now
        _last_cpu["usage_usec"] = usage_usec
    except Exception:
        pass
    return stats


def resolve_audio_url(raw: str):
    try:
        out = subprocess.run(
            ["yt-dlp", "-f", "worstaudio/worst", "-g", "--no-warnings", raw],
            capture_output=True, text=True, timeout=30,
        )
        lines = [line for line in out.stdout.strip().splitlines() if line]
        if lines:
            return lines[-1]
    except Exception:
        pass
    return None


def get_audio_url():
    global current_audio_url
    with state_lock:
        url, display = current_audio_url, current_display_url
    if url is None:
        url = resolve_audio_url(display)
        with state_lock:
            current_audio_url = url
    return url


def set_stream_url(url: str) -> None:
    global current_display_url, current_audio_url
    resolved = resolve_audio_url(url)
    with state_lock:
        current_display_url = url
        if resolved:
            current_audio_url = resolved
        transcript.clear()  # old transcript no longer applies to the new source


def _norm(word: str) -> str:
    """Lowercase and strip punctuation, for matching only - the original
    (differently-capitalized/punctuated) word is still what gets returned,
    since whisper transcribes the same overlapping audio slightly
    differently wording-wise each time it appears in a chunk."""
    return word.strip(".,!?\"'").lower()


def trim_overlap(prev_text: str, new_text: str, min_overlap=6, search_range=30) -> str:
    """Rolling audio chunks often re-capture a chunk of the previous
    chunk's tail - sometimes just a few words, sometimes most of it -
    which whisper then transcribes independently (and slightly
    differently worded/punctuated) each time. Search for the longest run
    of words from the end of prev_text that also appears near the start
    of new_text, and drop everything through that match.

    min_overlap is deliberately not small: a short common phrase (a few
    filler words) can coincidentally match without being real overlap,
    which would wrongly eat real new content. Requiring a longer match
    makes a coincidental hit much less likely. The search is also capped
    to near the start of new_text, since a genuine boundary overlap
    always shows up there, not deep into the chunk."""
    prev_words = prev_text.split()
    new_words = new_text.split()
    tail = [_norm(w) for w in prev_words[-search_range:]]
    window = [_norm(w) for w in new_words[:search_range]]
    for n in range(min(len(tail), search_range), min_overlap - 1, -1):
        phrase = tail[-n:]
        for start in range(len(window) - n + 1):
            if window[start:start + n] == phrase:
                return " ".join(new_words[start + n:])
    return new_text


def audio_loop():
    global status
    chunk_path = "/tmp/live_caption_chunk.wav"
    while True:
        try:
            audio_url = get_audio_url()
            if audio_url is None:
                raise RuntimeError("could not resolve audio URL")

            with state_lock:
                status["audio"] = "running"

            r = subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-i", audio_url, "-t", str(CHUNK_SECONDS), "-vn",
                 "-ar", "16000", "-ac", "1", "-f", "wav", chunk_path],
                capture_output=True, timeout=CHUNK_SECONDS + 20,
            )
            if r.returncode != 0:
                raise RuntimeError(r.stderr.decode(errors="replace")[:300])

            wr = subprocess.run(
                [WHISPER_BIN, "-m", WHISPER_MODEL, "-f", chunk_path, "-np", "-nt"],
                capture_output=True, text=True, timeout=60,
            )
            text = wr.stdout.strip()
            if text:
                ts = datetime.now().strftime("%H:%M:%S")
                with state_lock:
                    if transcript:
                        text = trim_overlap(transcript[-1][1], text).strip()
                    if text and (not transcript or transcript[-1][1] != text):
                        transcript.append((ts, text))
        except Exception as e:
            with state_lock:
                status["audio"] = f"error: {e}"
            time.sleep(5)


PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Live Captions</title>
<style>
  body { font-family: -apple-system, sans-serif; max-width: 700px; margin: 30px auto; padding: 0 16px; background: #111; color: #eee; }
  h1 { font-size: 1.8rem; margin-bottom: 2px; }
  .sub { color: #888; font-size: 1rem; margin-bottom: 10px; }
  .status { color: #888; font-size: 1rem; margin-bottom: 12px; }
  .bar { display: flex; gap: 8px; margin-bottom: 16px; }
  .bar input { flex: 1; font-size: 1.05rem; padding: 8px 10px; background: #1a1a1a; border: 1px solid #333; color: #eee; border-radius: 4px; }
  .bar button { font-size: 1.05rem; padding: 8px 16px; border: none; background: #2c3e50; color: white; border-radius: 4px; cursor: pointer; }
  audio { width: 100%; margin-bottom: 16px; }
  #transcript { background: #1a1a1a; border: 1px solid #333; padding: 12px; height: 300px; overflow-y: auto; font-size: 0.95rem; line-height: 1.5; }
  .ts { color: #6cf; margin-right: 8px; }
</style>
</head>
<body>
<h1>Live Captions</h1>
<div class="sub">whisper.cpp, tiny.en model (quantized) - CPU only</div>
<div class="bar">
  <input id="urlbox" type="text" placeholder="Paste a YouTube URL...">
  <button onclick="setUrl()">Load</button>
</div>
<div class="status" id="status"></div>
<audio id="player" src="/stream.audio" autoplay muted></audio>
<button id="unmute" onclick="unmute()" style="position: fixed; top: 12px; right: 12px; font-size: 1.05rem; padding: 8px 16px; border: none; border-radius: 4px; background: #2c3e50; color: white; cursor: pointer;">&#128266; Unmute</button>
<div id="transcript"></div>
<script>
function unmute() {
  const p = document.getElementById('player');
  p.muted = false;
  document.getElementById('unmute').style.display = 'none';
}
function setUrl() {
  const url = document.getElementById('urlbox').value.trim();
  if (!url) return;
  fetch('/set_url?url=' + encodeURIComponent(url)).then(() => {
    document.getElementById('player').src = '/stream.audio?r=' + Date.now();
  });
}
function refreshTranscript() {
  fetch('/transcript.json').then(r => r.json()).then(data => {
    const el = document.getElementById('transcript');
    el.innerHTML = data.lines.map(l => `<div><span class="ts">[${l[0]}]</span>${l[1]}</div>`).join('');
    el.scrollTop = el.scrollHeight;
    const s = data.status;
    let statusText = 'audio: ' + s.audio;
    if (s.cpu_pct !== undefined) statusText += ' | cpu: ' + s.cpu_pct + '%';
    if (s.mem_mb !== undefined) {
      statusText += ' | mem: ' + s.mem_mb + ' MB';
      if (s.mem_pct !== undefined) statusText += ' (' + s.mem_pct + '%)';
    }
    document.getElementById('status').textContent = statusText;
    if (document.activeElement !== document.getElementById('urlbox')) {
      document.getElementById('urlbox').value = data.status.stream_url || '';
    }
  });
}
setInterval(refreshTranscript, 3000);
refreshTranscript();
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
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/stream.audio":
            audio_url = get_audio_url()
            if audio_url is None:
                self.send_response(503)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/webm")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            proc = subprocess.Popen(
                ["ffmpeg", "-loglevel", "error",
                 "-i", audio_url,
                 "-c:a", "libopus", "-b:a", "64k",
                 "-f", "webm", "-"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            with state_lock:
                active_procs.add(proc)
            try:
                while True:
                    # read1(), not read(): see stream-filter for why.
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

        elif parsed.path == "/transcript.json":
            with state_lock:
                lines = list(transcript)
                st = dict(status)
                st["stream_url"] = current_display_url
            st.update(get_system_stats())
            body = json.dumps({"lines": lines, "status": st}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        elif parsed.path == "/set_url":
            url = parse_qs(parsed.query).get("url", [""])[0].strip()
            body = b"ok"
            if url:
                set_stream_url(url)
            else:
                body = b"missing url"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    threading.Thread(target=audio_loop, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()
