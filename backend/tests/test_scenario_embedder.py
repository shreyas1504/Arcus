"""shared_embedder() (PLAN.md 3e): one ONNX embedder per process for Research and Scenario Lab."""

from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from research import embedder, qa

ROOT = Path(__file__).resolve().parents[2]


class _FakeOnnxEmbedder:
    created: list[_FakeOnnxEmbedder] = []

    def __init__(self, *args, **kwargs):
        time.sleep(0.01)  # widen the race window for the threaded test
        _FakeOnnxEmbedder.created.append(self)


@pytest.fixture
def fake_onnx(monkeypatch):
    _FakeOnnxEmbedder.created = []
    monkeypatch.setattr(embedder, "OnnxEmbedder", _FakeOnnxEmbedder)
    monkeypatch.setattr(embedder, "_shared", None)
    return _FakeOnnxEmbedder


def test_shared_embedder_singleton(fake_onnx):
    first = embedder.shared_embedder()
    assert embedder.shared_embedder() is first
    assert len(fake_onnx.created) == 1

    research_qa = qa.ResearchQA(nvidia_api_key="test-key")
    research_qa._collection = object()  # skip Chroma; only the embedder is under test
    research_qa._load()
    assert research_qa._embedder is first, "Research QA must use the shared instance"
    assert len(fake_onnx.created) == 1


def test_shared_embedder_is_thread_safe(fake_onnx):
    results = []
    threads = [threading.Thread(target=lambda: results.append(embedder.shared_embedder())) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(fake_onnx.created) == 1
    assert all(r is results[0] for r in results)


def test_research_tests_still_pass():
    """The existing Research suite has no regressions with the shared embedder."""
    files = sorted(str(p) for p in (ROOT / "backend" / "tests").glob("test_research*.py"))
    assert files, "research tests not found"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-2000:]
