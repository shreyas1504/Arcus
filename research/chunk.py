"""Split normalized SEC documents into overlapping, metadata-rich chunks."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable

from research import EMBEDDING_MODEL

DEFAULT_DATA_DIR = Path(os.getenv("RESEARCH_DATA_DIR", "research/data"))
DEFAULT_INPUT = DEFAULT_DATA_DIR / "documents.jsonl"
DEFAULT_OUTPUT = DEFAULT_DATA_DIR / "chunks.jsonl"
CHUNK_TOKENS = 800
CHUNK_OVERLAP = 100


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def chunk_document(
    document: dict[str, Any],
    tokenizer: Any,
    *,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    if chunk_tokens <= 0 or overlap < 0 or overlap >= chunk_tokens:
        raise ValueError("Require chunk_tokens > 0 and 0 <= overlap < chunk_tokens")
    source = document["text"]
    # Slice the original text by character offsets: decoding tokens from the
    # uncased tokenizer lowercases and splits numbers ("$12.1B" -> "$ 12. 1b").
    offsets = tokenizer(
        source, add_special_tokens=False, return_offsets_mapping=True
    )["offset_mapping"]
    step = chunk_tokens - overlap
    chunks: list[dict[str, Any]] = []
    for ordinal, start in enumerate(range(0, len(offsets), step)):
        window = offsets[start : start + chunk_tokens]
        if not window:
            break
        text = source[window[0][0] : window[-1][1]].strip()
        if not text:
            continue
        digest = hashlib.sha256(
            f"{document['document_id']}:{ordinal}:{text}".encode("utf-8")
        ).hexdigest()[:20]
        chunks.append(
            {
                "chunk_id": f"{document['document_id']}:{ordinal}:{digest}",
                "document_id": document["document_id"],
                "ordinal": ordinal,
                "ticker": document["ticker"],
                "form": document["form"],
                "filing_date": document["filing_date"],
                "report_date": document.get("report_date", ""),
                "year": document["year"],
                "section": document["section"],
                "accession": document["accession"],
                "url": document["url"],
                "text": text,
                "token_count": len(window),
            }
        )
        if start + chunk_tokens >= len(offsets):
            break
    return chunks


def chunk_documents(
    documents: Iterable[dict[str, Any]],
    *,
    model_name: str = EMBEDDING_MODEL,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # Tokenization here measures/slices a document; model inference happens
    # later in store.py with safe subwindows, so do not warn at 512 tokens.
    tokenizer.model_max_length = 1_000_000_000
    chunks: list[dict[str, Any]] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                tokenizer,
                chunk_tokens=chunk_tokens,
                overlap=overlap,
            )
        )
    return chunks


def write_chunks(
    input_path: Path = DEFAULT_INPUT,
    output_path: Path = DEFAULT_OUTPUT,
    *,
    model_name: str = EMBEDDING_MODEL,
    chunk_tokens: int = CHUNK_TOKENS,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict[str, Any]]:
    chunks = chunk_documents(
        load_jsonl(input_path),
        model_name=model_name,
        chunk_tokens=chunk_tokens,
        overlap=overlap,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(chunk, ensure_ascii=False) + "\n" for chunk in chunks),
        encoding="utf-8",
    )
    return chunks


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunk normalized SEC filings")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    parser.add_argument("--chunk-tokens", type=int, default=CHUNK_TOKENS)
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    args = parser.parse_args()
    chunks = write_chunks(
        args.input,
        args.output,
        model_name=args.model,
        chunk_tokens=args.chunk_tokens,
        overlap=args.overlap,
    )
    print(f"Wrote {len(chunks)} chunks to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

