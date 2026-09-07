#!/usr/bin/env python3
"""Persistent status/progress server. Started once at pod boot, never exits."""
import os
import sys
import time
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
LOG_FILE = sys.argv[2] if len(sys.argv) > 2 else "/var/log/console.log"

PAGE_TEMPLATE = """<!doctype html>
<title>ceramics</title>
<style>
  body{background:#111;color:#ddd;font:13px/1.5 ui-monospace,Menlo,monospace;margin:0}
  #log{white-space:pre-wrap;padding:1rem}
</style>
<pre id="log">%s</pre>
<script>
  const log = document.getElementById("log");
  window.scrollTo(0, document.body.scrollHeight);
  new EventSource("/events").onmessage = (e) => {
    log.textContent += e.data + "\\n";
    window.scrollTo(0, document.body.scrollHeight);
  };
</script>
"""


def read_current():
    try:
        with open(LOG_FILE, "r") as f:
            return f.read()
    except OSError:
        return ""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/events":
            self.handle_events()
            return

        current = read_current()
        body = escape(current) if current else "nothing running yet — ask claude to start something"
        page = PAGE_TEMPLATE % body
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def handle_events(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        try:
            pos = os.stat(LOG_FILE).st_size
        except OSError:
            pos = 0

        while True:
            time.sleep(0.5)
            try:
                size = os.stat(LOG_FILE).st_size
            except OSError:
                continue
            if size < pos:
                pos = 0  # file was replaced/truncated for a new recipe
            if size <= pos:
                continue
            with open(LOG_FILE, "r") as f:
                f.seek(pos)
                chunk = f.read()
            pos = size
            try:
                for line in chunk.splitlines():
                    if line:
                        self.wfile.write(f"data: {line}\n\n".encode("utf-8"))
                self.wfile.flush()
            except BrokenPipeError:
                return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
