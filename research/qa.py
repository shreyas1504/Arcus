"""Ticker-filtered SEC retrieval and grounded Nemotron question answering."""

from __future__ import annotations

import os
import re
import threading
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from research import COLLECTION_NAME, EMBEDDING_MODEL, QUERY_INSTRUCTION

NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NEMOTRON_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
DEFAULT_CHROMA_DIR = Path(
    os.getenv(
        "RESEARCH_CHROMA_DIR",
        str(Path(os.getenv("RESEARCH_DATA_DIR", "research/data")) / "chroma"),
    )
)
NOT_FOUND = "Not found in the filings."
NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])[-+\u2212]?\$?\d[\d,]*(?:\.\d+)?%?")
CITATION_RE = re.compile(r"\[(\d+)]")
ABBREVIATION_END_RE = re.compile(
    r"(?:\b(?:U\.S|U\.K|E\.U|Inc|Corp|Co|Ltd|No|Nos|vs|approx|e\.g|i\.e)|\b[A-Z])\.$"
)
THINK_RE = re.compile(r"<think>.*?</think>", flags=re.IGNORECASE | re.DOTALL)

SYSTEM_PROMPT = """You are Arcus Research, a filing-only research assistant.

Rules:
1. Use only the numbered SEC filing excerpts provided by the user.
2. End every sentence and every bullet, including introductory lines, with one
or more excerpt citations such as [1].
3. Every number in the answer must appear verbatim in at least one cited excerpt.
4. Never use outside knowledge, inference, estimates, or unstated calculations.
5. If the excerpts do not directly contain the answer, reply exactly:
Not found in the filings.
6. Do not add a heading, preface, disclaimer, or source list.
"""


@dataclass(frozen=True)
class RetrievedChunk:
    citation: int
    chunk_id: str
    text: str
    ticker: str
    form: str
    filing_date: str
    year: str
    section: str
    url: str
    distance: float | None = None

    def public_citation(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("distance", None)
        data["excerpt"] = data.pop("text")
        return data


@dataclass(frozen=True)
class QAResult:
    answer: str
    citations: list[dict[str, Any]]
    retrieved_sections: list[str]
    validation_errors: list[str]


def _canonical_number(token: str) -> Decimal | None:
    clean = (
        token.replace("$", "")
        .replace(",", "")
        .replace("%", "")
        .replace("\u2212", "-")
        .lstrip("+")
    )
    try:
        return Decimal(clean).normalize()
    except InvalidOperation:
        return None


def unsupported_numbers(answer: str, excerpts: list[RetrievedChunk]) -> list[str]:
    answer_without_citations = CITATION_RE.sub("", answer)
    source_values = {
        value
        for chunk in excerpts
        for token in NUMBER_RE.findall(chunk.text)
        if (value := _canonical_number(token)) is not None
    }
    unsupported: list[str] = []
    for token in NUMBER_RE.findall(answer_without_citations):
        value = _canonical_number(token)
        if value not in source_values and token not in unsupported:
            unsupported.append(token)
    return unsupported


def _factual_units(answer: str) -> list[str]:
    units: list[str] = []
    for line in answer.splitlines():
        clean = re.sub(r"^\s*[-*]\s*", "", line).strip()
        if not clean:
            continue
        line_units: list[str] = []
        for piece in re.split(r"(?<=[.!?])\s+", clean):
            piece = piece.strip()
            if not piece:
                continue
            if line_units and ABBREVIATION_END_RE.search(line_units[-1]):
                line_units[-1] = f"{line_units[-1]} {piece}"
            else:
                line_units.append(piece)
        units.extend(line_units)
    return units


def validate_answer(answer: str, excerpts: list[RetrievedChunk]) -> list[str]:
    clean = answer.strip()
    if clean == NOT_FOUND:
        return []
    errors: list[str] = []
    valid_ids = {chunk.citation for chunk in excerpts}
    used_ids = {int(value) for value in CITATION_RE.findall(clean)}
    invalid = sorted(used_ids - valid_ids)
    if not used_ids:
        errors.append("No citations were used")
    if invalid:
        errors.append(f"Invalid citation IDs: {invalid}")
    uncited = [unit for unit in _factual_units(clean) if not CITATION_RE.search(unit)]
    if uncited:
        errors.append(f"Uncited factual sentences: {uncited[:3]}")
    numbers = unsupported_numbers(clean, excerpts)
    if numbers:
        errors.append(f"Numbers absent from excerpts: {numbers}")
    return errors


def build_user_prompt(question: str, excerpts: list[RetrievedChunk]) -> str:
    blocks = []
    for chunk in excerpts:
        blocks.append(
            f"[{chunk.citation}] {chunk.ticker} | {chunk.form} | "
            f"{chunk.filing_date} | {chunk.section}\n{chunk.text}"
        )
    return (
        "SEC filing excerpts:\n\n"
        + "\n\n".join(blocks)
        + f"\n\nQuestion: {question}\n\nAnswer using only the excerpts."
    )


def _diversify_sections(candidates: list[Any]) -> list[Any]:
    """Order candidates as the best chunk of each section first, then by rank.

    Avoids returning near-duplicate chunks from one long section.
    """
    seen: set[str] = set()
    leaders, rest = [], []
    for candidate in candidates:
        section = str(candidate[2]["section"])
        (rest if section in seen else leaders).append(candidate)
        seen.add(section)
    return leaders + rest


class ResearchQA:
    def __init__(
        self,
        *,
        chroma_dir: Path = DEFAULT_CHROMA_DIR,
        embedding_model: str = EMBEDDING_MODEL,
        nvidia_api_key: str | None = None,
        model: str | None = None,
        top_k: int = 6,
    ):
        self.chroma_dir = chroma_dir
        self.embedding_model_name = embedding_model
        self.api_key = nvidia_api_key or os.getenv("NVIDIA_API_KEY", "")
        self.base_url = NVIDIA_BASE_URL
        self.model_name = model or os.getenv("RESEARCH_MODEL") or DEFAULT_NEMOTRON_MODEL
        self.top_k = top_k
        self._embedder: Any = None
        self._collection = None
        self._lock = threading.Lock()

    def _load(self) -> None:
        with self._lock:
            if self._collection is None:
                from research.store import chroma_client

                self._collection = chroma_client(self.chroma_dir).get_collection(COLLECTION_NAME)
            if self._embedder is None:
                from research.embedder import shared_embedder

                self._embedder = shared_embedder()

    def ready(self) -> bool:
        try:
            self._load()
            return bool(self._collection and self._collection.count() > 0)
        except Exception:
            return False

    def retrieve(self, question: str, tickers: list[str]) -> list[RetrievedChunk]:
        self._load()
        assert self._embedder is not None
        query = QUERY_INSTRUCTION + question.strip()
        embedding = self._embedder.encode(
            [query], normalize_embeddings=True, show_progress_bar=False
        )[0].tolist()
        # Query each ticker separately so one company cannot crowd another out
        # of a comparison question.
        per_ticker: list[list[tuple[str, str, dict[str, Any], float]]] = []
        for ticker in tickers:
            result = self._collection.query(
                query_embeddings=[embedding],
                n_results=self.top_k * 10,
                where={"ticker": ticker},
                include=["documents", "metadatas", "distances"],
            )
            candidates = list(
                zip(
                    result.get("ids", [[]])[0],
                    result.get("documents", [[]])[0],
                    result.get("metadatas", [[]])[0],
                    result.get("distances", [[]])[0],
                )
            )
            if candidates:
                per_ticker.append(_diversify_sections(candidates))

        selected: list[tuple[str, str, dict[str, Any], float]] = []
        per_ticker.sort(key=lambda ranked: ranked[0][3])
        while len(selected) < self.top_k and any(per_ticker):
            for ranked in per_ticker:
                if ranked and len(selected) < self.top_k:
                    selected.append(ranked.pop(0))
        selected.sort(key=lambda candidate: candidate[3])

        return [
            RetrievedChunk(
                citation=citation,
                chunk_id=chunk_id,
                text=text,
                ticker=str(metadata["ticker"]),
                form=str(metadata["form"]),
                filing_date=str(metadata["filing_date"]),
                year=str(metadata["year"]),
                section=str(metadata["section"]),
                url=str(metadata["url"]),
                distance=float(distance),
            )
            for citation, (chunk_id, text, metadata, distance) in enumerate(selected, start=1)
        ]

    def _generate(self, user_prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("NVIDIA_API_KEY is not configured")
        from openai import OpenAI

        client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=25,
            max_retries=2,
        )
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            top_p=1,
            max_tokens=700,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        return THINK_RE.sub("", response.choices[0].message.content or "").strip()

    def answer(self, question: str, tickers: list[str]) -> QAResult:
        excerpts = self.retrieve(question, tickers)
        if not excerpts:
            return QAResult(NOT_FOUND, [], [], [])

        prompt = build_user_prompt(question, excerpts)
        answer = self._generate(prompt).strip()
        errors = validate_answer(answer, excerpts)
        if errors:
            repair = (
                f"{prompt}\n\nYour previous answer failed validation:\n"
                + "\n".join(f"- {error}" for error in errors)
                + f"\n\nReturn a corrected answer, or exactly: {NOT_FOUND}"
            )
            answer = self._generate(repair).strip()
            errors = validate_answer(answer, excerpts)
        if errors:
            answer = NOT_FOUND

        used = {int(value) for value in CITATION_RE.findall(answer)}
        citations = [
            chunk.public_citation() for chunk in excerpts if chunk.citation in used
        ]
        sections = [f"{chunk.ticker}:{chunk.section}" for chunk in excerpts]
        return QAResult(answer, citations, sections, errors)

