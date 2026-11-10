"""Download and normalize the Arcus Research SEC filing corpus.

Usage:
    SEC_USER_AGENT="Your Name your@email.com" python -m research.ingest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from backend.config import RESEARCH_TICKER_UNIVERSE

SEC_DATA = "https://data.sec.gov"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_DATA_DIR = Path(os.getenv("RESEARCH_DATA_DIR", "research/data"))
DOCUMENTS_PATH = DEFAULT_DATA_DIR / "documents.jsonl"
MANIFEST_PATH = DEFAULT_DATA_DIR / "manifest.json"

ITEM_SPECS = {
    "Item 1 Business": (
        r"(?:^item\s+1[\s.:\-—]*b\s*usiness\b|^item\s+1\.?\s*$|^b\s*usiness(?:\s+description)?\.?\s*$|"
        r"^our\s+business\s*$)",
        [
            r"^item\s+1a[\s.:\-—]*ris\s*k\s+factors\b",
            r"^item\s+1a\.?\s*$",
            r"^ris\s*k\s+factors\.?\s*$",
            # Topic-ordered 10-Ks (Intel) put MD&A directly after the business section.
            r"^management['’]s\s+discussion\s+and\s+analysis\s*$",
        ],
    ),
    "Item 1A Risk Factors": (
        r"(?:^item\s+1a[\s.:\-—]*ris\s*k\s+factors\b|^item\s+1a\.?\s*$|^ris\s*k\s+factors\.?\s*$)",
        [
            r"^item\s+1b(?:[\s.:\-—]*unresolved\s+staff\s+comments)?\b",
            r"^item\s+1c(?:[\s.:\-—]*cybersecurity)?\b",
            r"^item\s+2(?:[\s.:\-—]*properties)?\b",
            r"^management['’]s\s+discussion\s+and\s+analysis",
            r"^financial\s+review\.?\s*$",
            r"^other\s+key\s+information\s*$",
        ],
    ),
    "Item 7 MD&A": (
        r"(?:^item\s+7[\s.:\-—]*management['’]s\s+discussion\s+and\s+analysis\b|"
        r"^item\s+7\.?\s*$|^management['’]s\s+discussion\s+and\s+analysis|"
        r"^financial\s+review\.?\s*$)",
        [
            r"^item\s+7a(?:[\s.:\-—]*quantitative\s+and\s+qualitative)?\b",
            r"^item\s+8(?:[\s.:\-—]*financial\s+statements)?\b",
            r"^consolidated\s+financial\s+statements\.?\s*$",
            r"^financial\s+statements\.?\s*$",
            r"^ris\s*k\s+factors\.?\s*$",
        ],
    ),
}


@dataclass(frozen=True)
class Filing:
    form: str
    accession: str
    filing_date: str
    report_date: str
    primary_document: str
    items: str

    @property
    def accession_compact(self) -> str:
        return self.accession.replace("-", "")


class SECClient:
    """Small SEC client with the required identity header and polite pacing."""

    def __init__(self, user_agent: str, max_requests_per_second: float = 8.0):
        if not user_agent or "@" not in user_agent:
            raise ValueError("SEC_USER_AGENT must contain your name and email address")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov",
            }
        )
        self._minimum_interval = 1.0 / max_requests_per_second
        self._last_request = 0.0

    def get(self, url: str, *, as_json: bool = False) -> Any:
        wait = self._minimum_interval - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)

        last_error: Exception | None = None
        for attempt in range(6):
            try:
                response = self.session.get(url, timeout=45)
                self._last_request = time.monotonic()
                if response.status_code == 429 or response.status_code >= 500:
                    response.raise_for_status()
                if response.status_code >= 400:
                    raise requests.HTTPError(
                        f"SEC request failed ({response.status_code}) for {url}",
                        response=response,
                    )
                return response.json() if as_json else response.text
            except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
                last_error = exc
                status = getattr(getattr(exc, "response", None), "status_code", None)
                if status is not None and status not in {429, 500, 502, 503, 504}:
                    raise
                if attempt == 5:
                    break
                time.sleep(min(2**attempt, 30))
        raise RuntimeError(f"SEC request failed after retries: {url}") from last_error


def _with_data_host(client: SECClient, url: str, *, as_json: bool = False) -> Any:
    """The SEC requires Host to match data.sec.gov for submissions requests."""
    old_host = client.session.headers.get("Host")
    client.session.headers["Host"] = "data.sec.gov"
    try:
        return client.get(url, as_json=as_json)
    finally:
        if old_host is None:
            client.session.headers.pop("Host", None)
        else:
            client.session.headers["Host"] = old_host


def resolve_ciks(client: SECClient) -> dict[str, str]:
    payload = client.get(SEC_TICKERS_URL, as_json=True)
    resolved: dict[str, str] = {}
    wanted = set(RESEARCH_TICKER_UNIVERSE)
    for row in payload.values():
        ticker = str(row["ticker"]).upper().replace(".", "-")
        if ticker in wanted:
            resolved[ticker] = str(row["cik_str"]).zfill(10)
    missing = wanted - resolved.keys()
    if missing:
        raise RuntimeError(f"SEC ticker mapping missing: {', '.join(sorted(missing))}")
    return resolved


def _recent_filings(submissions: dict[str, Any]) -> list[Filing]:
    recent = submissions.get("filings", {}).get("recent", {})
    keys = (
        "form",
        "accessionNumber",
        "filingDate",
        "reportDate",
        "primaryDocument",
        "items",
    )
    row_count = len(recent.get("form", []))
    filings: list[Filing] = []
    for index in range(row_count):
        values = {key: (recent.get(key) or [""] * row_count)[index] for key in keys}
        filings.append(
            Filing(
                form=str(values["form"]),
                accession=str(values["accessionNumber"]),
                filing_date=str(values["filingDate"]),
                report_date=str(values["reportDate"]),
                primary_document=str(values["primaryDocument"]),
                items=str(values["items"]),
            )
        )
    return filings


def select_filings(
    filings: Iterable[Filing], *, earnings_limit: int | None = 2
) -> tuple[Filing, list[Filing]]:
    rows = list(filings)
    ten_k = next((row for row in rows if row.form == "10-K"), None)
    earnings_candidates = [
        row
        for row in rows
        if row.form == "8-K" and "2.02" in {item.strip() for item in row.items.split(",")}
    ]
    earnings = (
        earnings_candidates[:earnings_limit]
        if earnings_limit is not None
        else earnings_candidates
    )
    if ten_k is None:
        raise RuntimeError("No recent non-amended 10-K found")
    if len(earnings_candidates) < 2:
        raise RuntimeError(f"Expected two Item 2.02 8-K filings, found {len(earnings)}")
    return ten_k, earnings


def filing_url(cik: str, filing: Filing, filename: str | None = None) -> str:
    cik_compact = str(int(cik))
    document = filename or filing.primary_document
    return f"{SEC_ARCHIVES}/{cik_compact}/{filing.accession_compact}/{document}"


def html_to_text(html: str) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
        soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    normalized = "\n".join(line for line in lines if line)
    # Inline XBRL sometimes splits heading words across independently tagged
    # spans (for example "RIS" + "K FACTORS"). Repair only known headings.
    repairs = {
        r"\bb\s*\n\s*usiness\b": "business",
        r"\bbusines\s*\n\s*s\b": "business",
        r"\bris\s*\n\s*k\b": "risk",
        r"\bdiscus\s*\n\s*sion\b": "discussion",
        r"\banaly\s*\n\s*sis\b": "analysis",
    }
    for pattern, replacement in repairs.items():
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    return normalized


def _extract_section(text: str, start_pattern: str, end_patterns: list[str]) -> str:
    flags = re.IGNORECASE | re.MULTILINE
    starts = list(re.finditer(start_pattern, text, flags=flags))
    candidates: list[str] = []
    for start in starts:
        following = text[start.end() :]
        ends = [
            match.start()
            for pattern in end_patterns
            if (match := re.search(pattern, following, flags=flags))
        ]
        if not ends:
            continue
        segment = text[start.start() : start.end() + min(ends)].strip()
        if len(segment) >= 500:
            candidates.append(segment)
    if not candidates:
        raise ValueError(f"Could not find a complete section beginning with {start_pattern!r}")
    return max(candidates, key=len)


def extract_10k_sections(text: str) -> tuple[dict[str, str], list[str]]:
    sections: dict[str, str] = {}
    warnings: list[str] = []
    for name, (start, ends) in ITEM_SPECS.items():
        try:
            sections[name] = _extract_section(text, start, ends)
        except ValueError as exc:
            warnings.append(f"{name}: {exc}")
    return sections, warnings


def extract_submission_document(
    submission_text: str, type_pattern: str
) -> tuple[str, str]:
    """Return (filename, body) for the first submission document of a type."""
    for document in re.findall(
        r"<DOCUMENT>(.*?)</DOCUMENT>", submission_text, flags=re.IGNORECASE | re.DOTALL
    ):
        type_match = re.search(r"<TYPE>\s*([^\r\n<]+)", document, flags=re.IGNORECASE)
        if not type_match or not re.fullmatch(
            type_pattern, type_match.group(1).strip(), flags=re.IGNORECASE
        ):
            continue
        filename_match = re.search(r"<FILENAME>\s*([^\r\n<]+)", document, flags=re.IGNORECASE)
        filename = filename_match.group(1).strip() if filename_match else "exhibit-99-1"
        body_match = re.search(
            r"<TEXT>(.*?)</TEXT>", document, flags=re.IGNORECASE | re.DOTALL
        )
        body = body_match.group(1) if body_match else document
        return filename, body
    raise ValueError(f"Filing contains no document matching {type_pattern}")


def extract_exhibit_99_1(submission_text: str) -> tuple[str, str]:
    """Return (filename, document body) for the first EX-99.1 document."""
    # A few issuers label the same earnings-release exhibit as EX-99 while the
    # linked filename/filing convention treats it as the sole 99.1 exhibit.
    return extract_submission_document(
        submission_text, r"EX-?99(?:[.\-_]?1)?"
    )


def _document_record(
    *,
    ticker: str,
    cik: str,
    filing: Filing,
    section: str,
    text: str,
    url: str,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "document_id": f"{ticker}:{filing.accession}:{section}",
        "ticker": ticker,
        "cik": cik,
        "form": filing.form,
        "filing_date": filing.filing_date,
        "report_date": filing.report_date,
        "year": (filing.report_date or filing.filing_date)[:4],
        "section": section,
        "accession": filing.accession,
        "url": url,
        "text": text,
        "warnings": warnings or [],
    }


def ingest_ticker(client: SECClient, ticker: str, cik: str) -> tuple[list[dict], dict]:
    submissions_url = f"{SEC_DATA}/submissions/CIK{cik}.json"
    submissions = _with_data_host(client, submissions_url, as_json=True)
    ten_k, earnings_candidates = select_filings(
        _recent_filings(submissions), earnings_limit=None
    )
    records: list[dict] = []
    filing_manifest: list[dict] = []

    ten_k_url = filing_url(cik, ten_k)
    ten_k_text = html_to_text(client.get(ten_k_url))
    sections, warnings = extract_10k_sections(ten_k_text)
    section_urls = {section: ten_k_url for section in sections}

    # Some issuers (notably Wells Fargo) incorporate Item 1A and Item 7 from
    # an annual report filed as EX-13. Fill only sections missing from the
    # primary 10-K, preserving the direct SEC URL for those excerpts.
    if len(sections) != len(ITEM_SPECS):
        submission_url = filing_url(cik, ten_k, f"{ten_k.accession}.txt")
        submission_text = client.get(submission_url)
        try:
            annual_filename, annual_body = extract_submission_document(
                submission_text, r"EX-?13(?:\..*)?"
            )
            annual_url = filing_url(cik, ten_k, annual_filename)
            annual_sections, _ = extract_10k_sections(html_to_text(annual_body))
            for section, text in annual_sections.items():
                if section not in sections:
                    sections[section] = text
                    section_urls[section] = annual_url
            warnings = [
                warning
                for warning in warnings
                if warning.split(":", 1)[0] not in sections
            ]
        except ValueError:
            pass
    if len(sections) != len(ITEM_SPECS):
        raise RuntimeError("10-K section extraction incomplete: " + "; ".join(warnings))
    for section, text in sections.items():
        records.append(
            _document_record(
                ticker=ticker,
                cik=cik,
                filing=ten_k,
                section=section,
                text=text,
                url=section_urls[section],
                warnings=warnings,
            )
        )
    filing_manifest.append(
        {
            "form": "10-K",
            "accession": ten_k.accession,
            "filing_date": ten_k.filing_date,
            "url": ten_k_url,
            "sections": sorted(sections),
            "warnings": warnings,
        }
    )

    skipped_earnings: list[str] = []
    earnings_loaded = 0
    for filing in earnings_candidates:
        submission_url = filing_url(cik, filing, f"{filing.accession}.txt")
        try:
            filename, exhibit = extract_exhibit_99_1(client.get(submission_url))
        except ValueError:
            skipped_earnings.append(filing.accession)
            continue
        exhibit_url = filing_url(cik, filing, filename)
        release_text = html_to_text(exhibit)
        if len(release_text) < 500:
            raise ValueError(f"{filing.accession} EX-99.1 contains too little text")
        records.append(
            _document_record(
                ticker=ticker,
                cik=cik,
                filing=filing,
                section="Earnings Release",
                text=release_text,
                url=exhibit_url,
            )
        )
        filing_manifest.append(
            {
                "form": "8-K EX-99.1",
                "accession": filing.accession,
                "filing_date": filing.filing_date,
                "url": exhibit_url,
                "sections": ["Earnings Release"],
                "warnings": [],
            }
        )
        earnings_loaded += 1
        if earnings_loaded == 2:
            break

    if earnings_loaded < 2:
        raise RuntimeError(
            "Expected two Item 2.02 filings with EX-99.1; "
            f"loaded {earnings_loaded}, skipped {', '.join(skipped_earnings) or 'none'}"
        )

    return records, {"ticker": ticker, "status": "ok", "filings": filing_manifest}


def run_ingestion(
    tickers: list[str] | None = None,
    *,
    data_dir: Path = DEFAULT_DATA_DIR,
    user_agent: str | None = None,
) -> dict:
    selected = [ticker.upper().replace(".", "-") for ticker in (tickers or RESEARCH_TICKER_UNIVERSE)]
    unsupported = sorted(set(selected) - set(RESEARCH_TICKER_UNIVERSE))
    if unsupported:
        raise ValueError(f"Unsupported research tickers: {', '.join(unsupported)}")

    client = SECClient(user_agent or os.getenv("SEC_USER_AGENT", ""))
    ciks = resolve_ciks(client)
    documents: list[dict] = []
    companies: list[dict] = []
    for ticker in selected:
        try:
            rows, company = ingest_ticker(client, ticker, ciks[ticker])
            documents.extend(rows)
            companies.append(company)
            print(f"{ticker}: {len(rows)} logical documents", flush=True)
        except Exception as exc:
            companies.append({"ticker": ticker, "status": "error", "error": str(exc), "filings": []})
            print(f"{ticker}: ERROR {exc}", flush=True)

    data_dir.mkdir(parents=True, exist_ok=True)
    documents_path = data_dir / "documents.jsonl"
    documents_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in documents),
        encoding="utf-8",
    )
    manifest = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tickers_requested": selected,
        "documents": len(documents),
        "companies_ok": sum(company["status"] == "ok" for company in companies),
        "companies": companies,
    }
    (data_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the Arcus SEC filing corpus")
    parser.add_argument("--tickers", nargs="*", help="Subset of the fixed research universe")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    args = parser.parse_args()
    manifest = run_ingestion(args.tickers, data_dir=args.data_dir)
    print(json.dumps(manifest, indent=2))
    return 0 if manifest["companies_ok"] == len(manifest["tickers_requested"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())

