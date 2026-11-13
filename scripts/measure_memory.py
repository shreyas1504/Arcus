"""Peak memory of the API with Arcus Research and Scenario Lab both warm (PLAN Step 7, C6).

    python scripts/measure_memory.py --research-data research/data --scenario-assets scenario/assets

Starts the real FastAPI app in-process with both features enabled, warms them, then
makes 10 Scenario Lab requests (real Yahoo prices) and 10 Research retrievals, and
reports peak resident memory against the budget (450 MB of Render's 512 MB).

No language-model calls: NVIDIA_API_KEY is removed, so the question parser falls back
and Research is measured on retrieval (BGE + Chroma), which is what holds memory.
Requests use the automation key, so no quota rows are written.

macOS reports much higher and noisier peaks than Render's Linux (Research alone peaks at
about 460-520 MB here against 338 MB measured on Render), so the comparable figure is
Scenario Lab's increment over warm Research. The budget check is
RENDER_RESEARCH_BASELINE_MB + increment <= BUDGET_MB; the raw peaks are reported too.
"""

from __future__ import annotations

import argparse
import json
import os
import resource
import secrets
import sys
import tempfile
import time
from pathlib import Path

BUDGET_MB = 450.0
RENDER_RESEARCH_BASELINE_MB = 338.0  # Research alone, measured on Render (render.yaml comments, README)
QUESTIONS = [
    "What if China blockades Taiwan?",
    "What if a major US bank fails?",
    "What if oil prices spike after a war in the Middle East?",
    "What if the Fed raises rates by a full point?",
    "What if a new pandemic shuts down travel?",
]
PORTFOLIOS = [
    [{"ticker": "NVDA", "weight": 0.5}, {"ticker": "XOM", "weight": 0.3}, {"ticker": "JPM", "weight": 0.2}],
    [{"ticker": "AAPL", "weight": 0.3}, {"ticker": "MSFT", "weight": 0.3}, {"ticker": "JNJ", "weight": 0.2},
     {"ticker": "PG", "weight": 0.2}],
]
RESEARCH_QUESTIONS = [
    ("What are the main risk factors?", ["NVDA"]),
    ("How does the company describe competition?", ["AMD"]),
    ("What did management say about data center demand?", ["NVDA", "AMD"]),
    ("What are the supply chain risks?", ["INTC"]),
    ("How is revenue recognized?", ["MSFT"]),
]


def peak_mb() -> float:
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / (1024 * 1024) if sys.platform == "darwin" else peak / 1024


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-data", type=Path, required=True)
    parser.add_argument("--scenario-assets", type=Path, required=True)
    args = parser.parse_args()

    key = secrets.token_hex(16)
    rate_dir = tempfile.mkdtemp(prefix="arcus-memory-")
    os.environ.update({
        "RESEARCH_ENABLED": "true",
        "SCENARIO_ENABLED": "true",
        "RESEARCH_DATA_DIR": str(args.research_data),
        "SCENARIO_ASSETS_DIR": str(args.scenario_assets),
        "SCENARIO_RATE_DB": str(Path(rate_dir) / "scenario.sqlite3"),
        "RESEARCH_RATE_DB": str(Path(rate_dir) / "research.sqlite3"),
        "AUTOMATION_KEY": key,
    })
    os.environ.pop("NVIDIA_API_KEY", None)
    os.environ.pop("SCENARIO_FAKE", None)

    from fastapi.testclient import TestClient

    from backend.main import app
    from backend.routers import research

    report: dict = {"budget_mb": BUDGET_MB, "steps": []}

    def step(name: str) -> None:
        report["steps"].append({"step": name, "peak_mb": round(peak_mb(), 1)})
        print(f"{name:45s} peak {peak_mb():7.1f} MB", flush=True)

    step("imported app")
    with TestClient(app) as client:
        step("startup (Research warmed)")
        status = client.get("/api/scenario/status").json()
        step(f"scenario status: {status.get('status')}")
        timings = []
        for i in range(10):
            body = {"scenario": QUESTIONS[i % len(QUESTIONS)], "holdings": PORTFOLIOS[i % len(PORTFOLIOS)]}
            t0 = time.time()
            response = client.post("/api/scenario/whatif", json=body, headers={"X-Automation-Key": key})
            timings.append(round(time.time() - t0, 2))
            if response.status_code != 200:
                print(f"scenario request {i} -> {response.status_code}: {response.text[:200]}", file=sys.stderr)
                return 1
        step("10 Scenario Lab requests")
        service = research.get_qa_service()
        for question, tickers in RESEARCH_QUESTIONS * 2:
            service.retrieve(question, tickers)
        step("10 Research retrievals")

    report["peak_mb"] = round(peak_mb(), 1)
    warm = next(s["peak_mb"] for s in report["steps"] if s["step"].startswith("startup"))
    report["scenario_increment_mb"] = round(report["peak_mb"] - warm, 1)
    report["projected_render_mb"] = round(RENDER_RESEARCH_BASELINE_MB + report["scenario_increment_mb"], 1)
    report["scenario_seconds"] = timings
    report["within_budget"] = report["projected_render_mb"] <= BUDGET_MB
    print(json.dumps(report, indent=1))
    return 0 if report["within_budget"] else 2


if __name__ == "__main__":
    sys.exit(main())
