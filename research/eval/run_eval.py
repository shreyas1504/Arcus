"""Run the 30-question Arcus Research retrieval and grounding benchmark."""

from __future__ import annotations

import argparse
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research.qa import NOT_FOUND, ResearchQA, unsupported_numbers

HERE = Path(__file__).parent
DEFAULT_QUESTIONS = HERE / "questions.jsonl"
DEFAULT_RESULTS = HERE / "results.md"
DEFAULT_PROGRESS = HERE / "results.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_case(service: ResearchQA, case: dict[str, Any], retrieval_only: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    chunks = service.retrieve(case["question"], [case["ticker"]])
    retrieval_ms = round((time.perf_counter() - started) * 1000)
    expected_section = case.get("expected_section")
    hit = expected_section is None or any(
        chunk.ticker == case["ticker"] and chunk.section == expected_section for chunk in chunks
    )
    row: dict[str, Any] = {
        **case,
        "retrieval_hit": hit,
        "retrieval_ms": retrieval_ms,
        "retrieved": [
            {
                "citation": chunk.citation,
                "ticker": chunk.ticker,
                "section": chunk.section,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in chunks
        ],
    }
    if retrieval_only:
        return row

    answer_started = time.perf_counter()
    result = service.answer(case["question"], [case["ticker"]])
    row.update(
        {
            "answer": result.answer,
            "citations": result.citations,
            "unsupported_numbers": unsupported_numbers(result.answer, chunks),
            "not_found_exact": result.answer == NOT_FOUND,
            "latency_ms": round((time.perf_counter() - answer_started) * 1000),
            "validation_errors": result.validation_errors,
        }
    )
    return row


def summarize(rows: list[dict[str, Any]], retrieval_only: bool) -> dict[str, Any]:
    answerable = [row for row in rows if row["answerable"]]
    negatives = [row for row in rows if not row["answerable"]]
    summary: dict[str, Any] = {
        "questions": len(rows),
        "retrieval_hits": sum(bool(row["retrieval_hit"]) for row in answerable),
        "retrieval_total": len(answerable),
        "retrieval_hit_rate": (
            sum(bool(row["retrieval_hit"]) for row in answerable) / len(answerable)
            if answerable
            else 0
        ),
    }
    if not retrieval_only:
        completed = [row for row in rows if not row.get("error")]
        latencies = [row["latency_ms"] for row in completed if "latency_ms" in row]
        grounded = [row for row in completed if not row.get("unsupported_numbers")]
        summary.update(
            {
                "api_errors": len(rows) - len(completed),
                "answered": sum(
                    1
                    for row in answerable
                    if not row.get("error") and not row.get("not_found_exact")
                ),
                "answerable_total": len(answerable),
                "number_grounded": len(grounded),
                "number_total": len(completed),
                "not_found_hits": sum(bool(row.get("not_found_exact")) for row in negatives),
                "not_found_total": len(negatives),
                "median_latency_ms": statistics.median(latencies) if latencies else None,
                "p95_latency_ms": (
                    sorted(latencies)[min(len(latencies) - 1, int(len(latencies) * 0.95))]
                    if latencies
                    else None
                ),
            }
        )
    return summary


def _seconds(milliseconds: float | None) -> str:
    return "n/a" if milliseconds is None else f"{milliseconds / 1000:.2f}s"


def write_markdown(
    path: Path,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    model: str,
    retrieval_only: bool,
) -> None:
    retrieval_pct = summary["retrieval_hit_rate"] * 100
    lines = [
        "# Arcus Research Evaluation",
        "",
        f"- Run: {datetime.now(timezone.utc).isoformat()}",
        f"- Model: `{model}`",
        f"- Questions: {summary['questions']}",
        "",
        "## Results",
        "",
        "| Metric | Result | Target |",
        "|---|---:|---:|",
        (
            f"| Retrieval hit rate | {summary['retrieval_hits']}/{summary['retrieval_total']} "
            f"({retrieval_pct:.1f}%) | ≥80% |"
        ),
    ]
    if not retrieval_only:
        lines.extend(
            [
                (
                    f"| Answers with no unsupported numbers | {summary['number_grounded']}/"
                    f"{summary['number_total']} | 100% |"
                ),
                (
                    f"| Exact not-found responses | {summary['not_found_hits']}/"
                    f"{summary['not_found_total']} | 5/5 |"
                ),
                f"| Median latency | {_seconds(summary['median_latency_ms'])} | <4s |",
                f"| p95 latency | {_seconds(summary['p95_latency_ms'])} | — |",
                (
                    f"| Answerable questions answered | {summary['answered']}/"
                    f"{summary['answerable_total']} | — |"
                ),
                f"| API errors | {summary['api_errors']} | 0 |",
            ]
        )
    failures = [
        row
        for row in rows
        if not row["retrieval_hit"]
        or (not retrieval_only and row.get("error"))
        or (not retrieval_only and row["answerable"] and row.get("not_found_exact"))
        or (not retrieval_only and row.get("unsupported_numbers"))
        or (
            not retrieval_only
            and not row["answerable"]
            and not row.get("not_found_exact")
        )
    ]
    lines.extend(["", "## Failures", ""])
    if not failures:
        lines.append("None.")
    else:
        for row in failures:
            reasons = []
            if not row["retrieval_hit"]:
                reasons.append("expected section absent from top 6")
            if not retrieval_only and row.get("error"):
                reasons.append(f"API error: {row['error'][:120]}")
            elif not retrieval_only and row["answerable"] and row.get("not_found_exact"):
                errors = "; ".join(row.get("validation_errors") or [])[:200]
                reasons.append(f"fell back to not-found ({errors or 'model declined'})")
            if row.get("unsupported_numbers"):
                reasons.append(f"unsupported numbers: {row['unsupported_numbers']}")
            if not row["answerable"] and not row.get("not_found_exact", True):
                reasons.append("did not return exact not-found response")
            lines.append(f"- `{row['id']}`: {'; '.join(reasons)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Arcus Research")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--progress", type=Path, default=DEFAULT_PROGRESS)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retrieval-only", action="store_true")
    args = parser.parse_args()

    cases = load_jsonl(args.questions)[: args.limit or None]
    existing = load_jsonl(args.progress) if args.resume and args.progress.exists() else []
    done = {row["id"] for row in existing}
    rows = list(existing)
    service = ResearchQA()

    args.progress.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"
    with args.progress.open(mode, encoding="utf-8") as progress:
        for case in cases:
            if case["id"] in done:
                continue
            try:
                row = run_case(service, case, args.retrieval_only)
            except Exception as exc:
                row = {**case, "retrieval_hit": False, "error": repr(exc)}
            rows.append(row)
            progress.write(json.dumps(row, ensure_ascii=False) + "\n")
            progress.flush()
            print(f"{len(rows)}/{len(cases)} {case['id']}", flush=True)

    summary = summarize(rows, args.retrieval_only)
    write_markdown(
        args.results,
        summary,
        rows,
        model=service.model_name,
        retrieval_only=args.retrieval_only,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

