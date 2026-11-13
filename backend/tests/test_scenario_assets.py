"""Scenario Lab deploy assets (PLAN Step 7, C6): what Render downloads at build time."""

from __future__ import annotations

import hashlib
import re
import tarfile
from pathlib import Path

import pytest

from scenario import engine, fetch_assets

ROOT = Path(__file__).resolve().parents[2]
LOCAL_ARCHIVE = ROOT / "scenario/raw/release/arcus-scenario-assets-v1.tar.gz"


def test_archive_members_are_what_the_engine_loads():
    assert set(fetch_assets.MEMBERS) == {"library.npz", "library.json", "factor_history.npz", "calibration.json"}
    # The engine reads calibration.json from its assets folder first.
    assert "calibration.json" in engine._calibration_path.__code__.co_consts


def test_render_points_the_engine_where_the_fetcher_unpacks():
    render = (ROOT / "render.yaml").read_text()
    match = re.search(r"key: SCENARIO_ASSETS_DIR\s+value: (\S+)", render)
    assert match and Path(match.group(1)) == Path("scenario/assets")
    assert "SCENARIO_DATA_DIR" not in render  # so the fetcher keeps its default, scenario/assets


def test_release_url_is_the_pinned_release():
    assert fetch_assets.ASSET_URL == (
        "https://github.com/shreyas1504/Arcus/releases/download/scenario-assets-v1/arcus-scenario-assets-v1.tar.gz"
    )


def test_render_build_fetches_scenario_assets_and_keeps_the_feature_off():
    render = (ROOT / "render.yaml").read_text()
    assert "python -m scenario.fetch_assets" in render
    assert re.search(r'key: SCENARIO_ENABLED\s+value: "false"', render)


def test_sha256_is_pinned_and_matches_the_built_archive():
    if not fetch_assets.ASSET_SHA256:
        pytest.skip("SHA256 is pinned when scenario-assets-v1 is published (C6, needs the user's OK)")
    assert re.fullmatch(r"[0-9a-f]{64}", fetch_assets.ASSET_SHA256)
    if LOCAL_ARCHIVE.exists():
        assert hashlib.sha256(LOCAL_ARCHIVE.read_bytes()).hexdigest() == fetch_assets.ASSET_SHA256


def test_local_archive_contains_exactly_the_members():
    if not LOCAL_ARCHIVE.exists():
        pytest.skip("no locally built archive (CI)")
    with tarfile.open(LOCAL_ARCHIVE) as archive:
        assert sorted(archive.getnames()) == sorted(fetch_assets.MEMBERS)
