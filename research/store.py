"""Embed SEC chunks with BGE and persist them in Chroma."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import chromadb
import numpy as np
from chromadb.config import Settings

from backend.config import RESEARCH_TICKER_UNIVERSE
from research import COLLECTION_NAME, EMBEDDING_MODEL
from research.chunk import DEFAULT_OUTPUT, load_jsonl, write_chunks

DEFAULT_DATA_DIR = Path(os.getenv("RESEARCH_DATA_DIR", "research/data"))
DEFAULT_CHROMA_DIR = Path(os.getenv("RESEARCH_CHROMA_DIR", str(DEFAULT_DATA_DIR / "chroma")))


def chroma_client(path: Path = DEFAULT_CHROMA_DIR):
    path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(path),
        settings=Settings(anonymized_telemetry=False),
    )


def _metadata(chunk: dict[str, Any]) -> dict[str, str | int | float | bool]:
    return {
        key: value
        for key, value in chunk.items()
        if key not in {"text", "chunk_id"} and isinstance(value, (str, int, float, bool))
    }


def verify_chunks(chunks: list[dict[str, Any]], tickers: list[str] | None = None) -> dict[str, list[str]]:
    expected = tickers or RESEARCH_TICKER_UNIVERSE
    coverage: dict[str, list[str]] = {}
    problems: list[str] = []
    for ticker in expected:
        ticker_chunks = [chunk for chunk in chunks if chunk["ticker"] == ticker]
        sections = sorted({chunk["section"] for chunk in ticker_chunks})
        coverage[ticker] = sections
        required = {"Item 1 Business", "Item 1A Risk Factors", "Item 7 MD&A", "Earnings Release"}
        if not required.issubset(set(sections)):
            problems.append(f"{ticker}: sections={sections or 'none'}")
        ten_k_accessions = {
            chunk["accession"] for chunk in ticker_chunks if chunk["form"] == "10-K"
        }
        earnings_accessions = {
            chunk["accession"]
            for chunk in ticker_chunks
            if chunk["section"] == "Earnings Release"
        }
        if len(ten_k_accessions) != 1 or len(earnings_accessions) != 2:
            problems.append(
                f"{ticker}: 10-K filings={len(ten_k_accessions)}, "
                f"earnings exhibits={len(earnings_accessions)}"
            )
    if problems:
        raise RuntimeError(f"Index source coverage incomplete: {'; '.join(problems)}")
    return coverage


def embed_long_texts(
    model: Any,
    texts: list[str],
    *,
    batch_size: int = 64,
    subwindow_overlap: int = 64,
) -> list[list[float]]:
    """Embed every token of ~800-token chunks despite BGE's 512-token limit."""
    tokenizer = model.tokenizer
    max_tokens = max(32, int(model.max_seq_length) - 2)
    step = max_tokens - subwindow_overlap
    pieces: list[str] = []
    owners: list[int] = []
    weights: list[int] = []
    for owner, text in enumerate(texts):
        token_ids = tokenizer.encode(text, add_special_tokens=False)
        for start in range(0, len(token_ids), step):
            window = token_ids[start : start + max_tokens]
            if not window:
                break
            pieces.append(tokenizer.decode(window, skip_special_tokens=True))
            owners.append(owner)
            weights.append(len(window))
            if start + max_tokens >= len(token_ids):
                break

    vectors = model.encode(
        pieces,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    sums = np.zeros((len(texts), vectors.shape[1]), dtype=np.float32)
    total_weights = np.zeros(len(texts), dtype=np.float32)
    for vector, owner, weight in zip(vectors, owners, weights):
        sums[owner] += vector * weight
        total_weights[owner] += weight
    sums /= total_weights[:, None]
    norms = np.linalg.norm(sums, axis=1, keepdims=True)
    sums /= np.maximum(norms, 1e-12)
    return sums.tolist()


def build_index(
    chunks_path: Path = DEFAULT_OUTPUT,
    chroma_dir: Path = DEFAULT_CHROMA_DIR,
    *,
    model_name: str = EMBEDDING_MODEL,
    collection_name: str = COLLECTION_NAME,
    batch_size: int = 64,
    verify: bool = True,
) -> dict[str, Any]:
    chunks = load_jsonl(chunks_path)
    if not chunks:
        raise RuntimeError(f"No chunks found in {chunks_path}")
    if verify:
        verify_chunks(chunks)

    client = chroma_client(chroma_dir)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
    collection = client.create_collection(
        collection_name,
        metadata={
            "hnsw:space": "cosine",
            "embedding_model": model_name,
            "schema_version": 1,
        },
    )
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [chunk["text"] for chunk in batch]
        embeddings = embed_long_texts(
            model,
            texts,
            batch_size=batch_size,
        )
        collection.upsert(
            ids=[chunk["chunk_id"] for chunk in batch],
            documents=texts,
            metadatas=[_metadata(chunk) for chunk in batch],
            embeddings=embeddings,
        )
        print(f"Embedded {min(start + len(batch), len(chunks))}/{len(chunks)}", flush=True)

    summary = {
        "collection": collection_name,
        "embedding_model": model_name,
        "chunks": collection.count(),
        "chroma_dir": str(chroma_dir),
    }
    (chroma_dir / "index_manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def ensure_index(data_dir: Path = DEFAULT_DATA_DIR, chroma_dir: Path = DEFAULT_CHROMA_DIR) -> dict:
    client = chroma_client(chroma_dir)
    try:
        collection = client.get_collection(COLLECTION_NAME)
        if collection.count() > 0:
            return {
                "collection": COLLECTION_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "chunks": collection.count(),
                "chroma_dir": str(chroma_dir),
                "existing": True,
            }
    except Exception:
        pass

    documents_path = data_dir / "documents.jsonl"
    chunks_path = data_dir / "chunks.jsonl"
    if not documents_path.exists():
        from research.ingest import run_ingestion

        run_ingestion(data_dir=data_dir)
    if not chunks_path.exists():
        write_chunks(documents_path, chunks_path)
    return build_index(chunks_path, chroma_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Arcus Research Chroma index")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--chroma-dir", type=Path, default=DEFAULT_CHROMA_DIR)
    parser.add_argument("--model", default=EMBEDDING_MODEL)
    parser.add_argument("--ensure-index", action="store_true")
    parser.add_argument("--skip-coverage-check", action="store_true")
    args = parser.parse_args()
    if args.ensure_index:
        summary = ensure_index(args.chunks.parent, args.chroma_dir)
    else:
        summary = build_index(
            args.chunks,
            args.chroma_dir,
            model_name=args.model,
            verify=not args.skip_coverage_check,
        )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

