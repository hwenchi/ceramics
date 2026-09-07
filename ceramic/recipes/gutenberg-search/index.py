#!/usr/bin/env python3
"""Index the corpus into a SQLite FTS5 table, one row per paragraph."""
import re
import sqlite3
from pathlib import Path

DATA_DIR = Path("/var/lib/recipes/gutenberg-search")
CORPUS_DIR = DATA_DIR / "corpus"
DB_PATH = DATA_DIR / "index.db"

START_RE = re.compile(r"\*\*\*\s*START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)
END_RE = re.compile(r"\*\*\*\s*END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK", re.I)


def strip_boilerplate(text: str) -> str:
    lines = text.splitlines()
    start = 0
    end = len(lines)
    for i, line in enumerate(lines):
        if START_RE.search(line):
            start = i + 1
            break
    for i, line in enumerate(lines):
        if END_RE.search(line):
            end = i
            break
    return "\n".join(lines[start:end])


def title_from_filename(path: Path) -> str:
    return path.stem.replace("_", " ")


def split_paragraphs(text: str):
    blocks = re.split(r"\n\s*\n", text)
    for block in blocks:
        collapsed = " ".join(block.split())
        if len(collapsed) < 2:
            continue
        yield collapsed


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE VIRTUAL TABLE paragraphs USING fts5(
            book UNINDEXED,
            para_index UNINDEXED,
            content
        )
        """
    )

    files = sorted(CORPUS_DIR.glob("*.txt"))
    total_paragraphs = 0
    for path in files:
        raw = path.read_text(encoding="utf-8", errors="replace")
        body = strip_boilerplate(raw)
        title = title_from_filename(path)

        rows = [
            (title, idx, para)
            for idx, para in enumerate(split_paragraphs(body))
        ]

        conn.executemany(
            "INSERT INTO paragraphs (book, para_index, content) VALUES (?, ?, ?)",
            rows,
        )
        total_paragraphs += len(rows)
        print(f"{title}: {len(rows)} paragraphs")

    conn.commit()
    conn.close()
    print(f"\nIndexed {len(files)} books, {total_paragraphs} paragraphs total -> {DB_PATH}")


if __name__ == "__main__":
    main()
