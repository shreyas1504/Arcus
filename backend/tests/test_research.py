"""Unit tests for the filing-only Arcus Research path."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.config import RESEARCH_TICKER_UNIVERSE
from backend.routers import research as research_router
from research.ingest import (
    Filing,
    extract_10k_sections,
    extract_exhibit_99_1,
    select_filings,
)
from research.qa import (
    NOT_FOUND,
    NVIDIA_BASE_URL,
    QAResult,
    ResearchQA,
    RetrievedChunk,
    validate_answer,
)

app = FastAPI()
app.include_router(research_router.router)


def filing(form: str, accession: str, items: str = "") -> Filing:
    return Filing(form, accession, "2026-01-01", "2025-12-31", "filing.htm", items)


def test_research_universe_is_fixed_to_21_companies():
    assert len(RESEARCH_TICKER_UNIVERSE) == 21
    assert "NVDA" in RESEARCH_TICKER_UNIVERSE
    assert "MU" in RESEARCH_TICKER_UNIVERSE


def test_selects_latest_10k_and_two_item_202_8ks():
    rows = [
        filing("10-K", "ten-k"),
        filing("8-K", "earnings-1", "2.02,9.01"),
        filing("8-K", "other", "8.01"),
        filing("8-K", "earnings-2", "2.02,9.01"),
        filing("8-K", "earnings-3", "2.02,9.01"),
    ]
    ten_k, earnings = select_filings(rows)
    assert ten_k.accession == "ten-k"
    assert [row.accession for row in earnings] == ["earnings-1", "earnings-2"]


def test_extracts_required_10k_sections():
    text = "\n".join(
        [
            "ITEM 1. Business",
            "Business details " * 100,
            "ITEM 1A. Risk Factors",
            "Risk details " * 100,
            "ITEM 1B. Unresolved Staff Comments",
            "ITEM 7. Management's Discussion and Analysis",
            "Management discussion " * 100,
            "ITEM 7A. Quantitative and Qualitative Disclosures",
        ]
    )
    sections, warnings = extract_10k_sections(text)
    assert set(sections) == {
        "Item 1 Business",
        "Item 1A Risk Factors",
        "Item 7 MD&A",
    }
    assert warnings == []


def test_extracts_exhibit_99_1_from_submission():
    submission = """
    <DOCUMENT><TYPE>8-K<TEXT>cover</TEXT></DOCUMENT>
    <DOCUMENT>
    <TYPE>EX-99.1
    <FILENAME>earnings.htm
    <TEXT><html><body>Revenue was $10.</body></html></TEXT>
    </DOCUMENT>
    """
    filename, body = extract_exhibit_99_1(submission)
    assert filename == "earnings.htm"
    assert "Revenue was $10" in body


@pytest.fixture
def excerpt() -> RetrievedChunk:
    return RetrievedChunk(
        citation=1,
        chunk_id="AAPL:test:0",
        text="The company reported net revenue of $10 million in 2025.",
        ticker="AAPL",
        form="8-K",
        filing_date="2025-10-30",
        year="2025",
        section="Earnings Release",
        url="https://www.sec.gov/example",
    )


def test_grounding_validator_accepts_cited_source_numbers(excerpt):
    assert validate_answer("Net revenue was $10 million in 2025 [1].", [excerpt]) == []


def test_grounding_validator_rejects_unsupported_numbers(excerpt):
    errors = validate_answer("Net revenue was $12 million [1].", [excerpt])
    assert any("$12" in error for error in errors)


def test_grounding_validator_rejects_uncited_claim(excerpt):
    errors = validate_answer("The company reported net revenue.", [excerpt])
    assert any("No citations" in error for error in errors)
    assert any("Uncited" in error for error in errors)


def test_not_found_is_always_valid(excerpt):
    assert validate_answer(NOT_FOUND, [excerpt]) == []


def test_nvidia_key_selects_nvidia_nemotron(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.delenv("RESEARCH_MODEL", raising=False)
    service = ResearchQA()
    assert service.api_key == "test-key"
    assert service.base_url == NVIDIA_BASE_URL
    assert service.model_name == "nvidia/nemotron-3-ultra-550b-a55b"


def test_daily_quota_is_persistent_and_atomic(tmp_path: Path):
    quota = research_router.DailyQuota(tmp_path / "quota.sqlite3", limit=2)
    assert quota.used("person", "2026-11-09") == 0
    assert quota.consume("person", "2026-11-09") == 1
    assert quota.consume("person", "2026-11-09") == 0
    with pytest.raises(ValueError):
        quota.consume("person", "2026-11-09")


def test_research_endpoint_returns_structured_citations(monkeypatch, tmp_path: Path, excerpt):
    class FakeService:
        def answer(self, question, tickers):
            return QAResult(
                answer="Net revenue was $10 million [1].",
                citations=[excerpt.public_citation()],
                retrieved_sections=["AAPL:Earnings Release"],
                validation_errors=[],
            )

    quota = research_router.DailyQuota(tmp_path / "api-quota.sqlite3")
    monkeypatch.setenv("RESEARCH_ENABLED", "true")
    monkeypatch.setattr(research_router, "get_qa_service", lambda: FakeService())
    monkeypatch.setattr(research_router, "get_quota", lambda: quota)

    response = TestClient(app).post(
        "/api/research/ask",
        json={
            "question": "What was revenue?",
            "tickers": ["AAPL"],
            "client_id": "research_test_client_123",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"].endswith("[1].")
    assert payload["citations"][0]["url"].startswith("https://www.sec.gov/")
    assert payload["remaining_today"] == 19


def test_research_endpoint_is_hidden_when_disabled(monkeypatch):
    monkeypatch.setenv("RESEARCH_ENABLED", "false")
    response = TestClient(app).post(
        "/api/research/ask",
        json={
            "question": "What was revenue?",
            "tickers": ["AAPL"],
            "client_id": "research_test_client_456",
        },
    )
    assert response.status_code == 404



def test_chunks_preserve_original_filing_text():
    from research.chunk import chunk_document

    class WhitespaceTokenizer:
        def __call__(self, text, **_):
            import re

            return {"offset_mapping": [m.span() for m in re.finditer(r"\S+", text)]}

    document = {
        "document_id": "V:earnings",
        "ticker": "V",
        "form": "8-K",
        "filing_date": "2026-10-27",
        "year": "2026",
        "section": "Earnings Release",
        "accession": "0000000000-26-000001",
        "url": "https://www.sec.gov/",
        "text": "Net revenue of $12.1B, up 13%.\nGAAP EPS of $3.19 per share.",
    }
    chunks = chunk_document(document, WhitespaceTokenizer(), chunk_tokens=6, overlap=2)

    assert chunks[0]["text"] == "Net revenue of $12.1B, up 13%."
    assert "$3.19" in chunks[-1]["text"]


def test_validator_does_not_split_sentences_on_abbreviations():
    excerpt = RetrievedChunk(
        1, "LLY:10-K:1:x", "U.S. patent protection may be challenged.", "LLY",
        "10-K", "2026-02-01", "2025", "Risk Factors", "https://www.sec.gov/",
    )
    answer = "Lilly discloses that its U.S. patents may be challenged [1]."

    assert validate_answer(answer, [excerpt]) == []
