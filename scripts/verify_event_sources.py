"""Check that every event's source_quote appears verbatim on its source page.

    python scripts/verify_event_sources.py scenario/events/1999_2012.jsonl [--cache DIR] [--out report.json]

For each event: download source_url, extract the page text, and look for the quote.
  exact  - found after normalizing only typography (curly quotes, dashes, spaces)
  loose  - found only after also ignoring case and punctuation (needs a human look)
  missing- not found on the page
  error  - the page could not be downloaded (needs a manual check)
Exit code 1 if any event is not `exact`. The script never edits event files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; arcus-event-verifier/1.0)"
TYPO = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "‛": "'", "′": "'",
        "“": '"', "”": '"', "„": '"', "″": '"',
        "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
        " ": " ", " ": " ", " ": " ", "​": "",
    }
)


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(TYPO)
    return re.sub(r"\s+", " ", text).strip()


def loose(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", normalize(text).lower()).strip()


def page_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return normalize(soup.get_text(" "))


def pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # optional dependency, only for PDF sources
        raise RuntimeError("source is a PDF; install pypdf to check it") from exc
    import io

    reader = PdfReader(io.BytesIO(data))
    return normalize(" ".join(page.extract_text() or "" for page in reader.pages))


def fetch(url: str, cache: Path | None) -> bytes:
    path = cache / (hashlib.sha256(url.encode()).hexdigest() + ".html") if cache else None
    if path is not None and path.exists():
        return path.read_bytes()
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(response.content)
    return response.content


def source_text(data: bytes) -> str:
    if data[:5] == b"%PDF-":
        return pdf_text(data)
    return page_text(data.decode("utf-8", errors="replace"))


def check(event: dict, cache: Path | None) -> dict:
    result = {"id": event["id"], "date": event["date"], "url": event["source_url"]}
    try:
        text = source_text(fetch(event["source_url"], cache))
    except Exception as exc:  # noqa: BLE001 - reported, never hidden
        return result | {"status": "error", "detail": f"{type(exc).__name__}: {exc}"[:200]}
    quote = normalize(event["source_quote"])
    if quote in text:
        return result | {"status": "exact"}
    if loose(quote) in loose(text):
        return result | {"status": "loose"}
    return result | {"status": "missing", "page_chars": len(text)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path)
    parser.add_argument("--cache", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    events = [json.loads(line) for line in args.events.read_text().splitlines() if line.strip()]
    results = []
    for event in events:
        results.append(check(event, args.cache))
        print(f"{results[-1]['status']:8} {event['id']}", flush=True)
        time.sleep(args.delay)

    counts: dict[str, int] = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print("summary:", counts)
    if args.out:
        args.out.write_text(json.dumps(results, indent=1) + "\n")
    return 0 if counts.get("exact", 0) == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
