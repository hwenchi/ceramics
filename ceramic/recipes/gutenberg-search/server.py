#!/usr/bin/env python3
"""Tiny full-text search web app over the paragraph-level SQLite FTS5 index.
Stdlib only - no dependencies, no build step."""
import html
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

DATA_DIR = Path("/var/lib/recipes/gutenberg-search")
DB_PATH = DATA_DIR / "index.db"
HOST = "0.0.0.0"
PORT = 8080

PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Classics Search</title>
<style>
  body {{ font-family: Georgia, serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #222; background: #fdfcf9; }}
  h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
  .sub {{ color: #777; font-size: 0.85rem; margin-bottom: 24px; }}
  form {{ display: flex; gap: 8px; margin-bottom: 28px; }}
  input[type=text] {{ flex: 1; font-size: 1rem; padding: 10px 12px; border: 1px solid #ccc; border-radius: 4px; }}
  button {{ font-size: 1rem; padding: 10px 18px; border: none; background: #2c3e50; color: white; border-radius: 4px; cursor: pointer; }}
  button:hover {{ background: #1a252f; }}
  .result {{ margin-bottom: 22px; padding-bottom: 18px; border-bottom: 1px solid #eee; }}
  .meta {{ font-size: 0.82rem; color: #888; margin-bottom: 4px; }}
  .meta b {{ color: #555; }}
  .snippet {{ line-height: 1.5; }}
  mark {{ background: #fff3a3; padding: 0 2px; }}
  .count {{ color: #777; font-size: 0.85rem; margin-bottom: 16px; }}
  .empty {{ color: #999; font-style: italic; }}
</style>
</head>
<body>
<h1>Classics Search</h1>
<div class="sub">Paragraph-level full-text search over public-domain novels (Project Gutenberg) - SQLite FTS5 + BM25 ranking</div>
<form onsubmit="return false">
  <input type="text" id="q" value="{query_escaped}" placeholder="Search for a word or phrase..." autofocus oninput="onType()">
</form>
<div id="results">{results}</div>
<script>
let debounceTimer = null;
function onType() {{
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(runSearch, 200);
}}
function runSearch() {{
  const q = document.getElementById('q').value;
  fetch('/results?q=' + encodeURIComponent(q)).then(r => r.text()).then(html => {{
    document.getElementById('results').innerHTML = html;
  }});
}}
</script>
</body>
</html>
"""


def sanitize_query(raw: str) -> str:
    """Keep only word characters and spaces so arbitrary user input can't
    break FTS5's query syntax (quotes, colons, wildcards, etc.)."""
    words = re.findall(r"\w+", raw, flags=re.UNICODE)
    return " ".join(words)


def render_results(raw_query: str) -> str:
    query = sanitize_query(raw_query)
    if not query:
        return ""

    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """
            SELECT book, para_index, snippet(paragraphs, 2, '<mark>', '</mark>', '...', 36)
            FROM paragraphs
            WHERE paragraphs MATCH ?
            ORDER BY rank
            LIMIT 30
            """,
            (query,),
        ).fetchall()
    except sqlite3.OperationalError:
        return '<div class="empty">No results (try a simpler query).</div>'
    finally:
        conn.close()

    if not rows:
        return '<div class="empty">No matches found.</div>'

    parts = [f'<div class="count">{len(rows)} result(s) for "{html.escape(query)}"</div>']
    for book, para_index, snippet in rows:
        parts.append(
            f'<div class="result">'
            f'<div class="meta"><b>{html.escape(book)}</b> - paragraph {para_index}</div>'
            f'<div class="snippet">{snippet}</div>'
            f"</div>"
        )
    return "\n".join(parts)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout quiet

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)
        raw_query = qs.get("q", [""])[0]

        if parsed.path == "/results":
            body = render_results(raw_query).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path != "/":
            self.send_response(404)
            self.end_headers()
            return

        body = PAGE_TEMPLATE.format(
            query_escaped=html.escape(raw_query, quote=True),
            results=render_results(raw_query),
        ).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Serving on http://{HOST}:{PORT}")
    server.serve_forever()
