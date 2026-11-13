"""Curated event library checks (PLAN.md Step 1).

Runs over every scenario/events/*.jsonl file, so Cursor's 1999_2012.jsonl and Claude's
2013_2026.jsonl are checked by the same rules once both are merged.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

from scenario import trading_calendar
from scenario.enums import Category, Nature, Split, Tool, split_for
from scenario.schemas import Event

EVENTS_DIR = Path(__file__).resolve().parents[2] / "scenario" / "events"
FILES = sorted(EVENTS_DIR.glob("*.jsonl"))

# File name -> (first year, last year, drafting tool), from PLAN Step 1.
FILE_RULES = {
    "1999_2012.jsonl": (1999, 2012, Tool.CURSOR),
    "2013_2026.jsonl": (2013, 2026, Tool.CLAUDE),
}

OUTCOME_WORDS = (
    "fell", "plunged", "rallied", "soared", "crashed", "recovered", "rebounded",
    "slumped", "tumbled", "surged",
)
OUTCOME_RE = re.compile(r"\b(" + "|".join(OUTCOME_WORDS) + r")\b", re.IGNORECASE)
PERCENT_RE = re.compile(r"%|\bper ?cent\b", re.IGNORECASE)
FUTURE_RE = re.compile(
    r"\b(later|subsequently|would go on|eventually|ultimately)\b", re.IGNORECASE
)
CLUSTER_WINDOW = 10  # trading days
MIN_PER_CATEGORY = 6
MIN_FAVORABLE = 25


def _rows() -> list[tuple[str, int, dict]]:
    rows = []
    for path in FILES:
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if line.strip():
                rows.append((path.name, lineno, json.loads(line)))
    return rows


ROWS = _rows()


def _events() -> list[Event]:
    return [Event.model_validate(raw) for _, _, raw in ROWS]


def _where(name: str, lineno: int) -> str:
    return f"{name}:{lineno}"


def test_event_files_exist():
    assert (EVENTS_DIR / "2013_2026.jsonl").exists()
    unknown = [p.name for p in FILES if p.name not in FILE_RULES]
    assert not unknown, f"unexpected event files: {unknown}"


def test_schema_valid():
    errors = []
    for name, lineno, raw in ROWS:
        try:
            Event.model_validate(raw)
        except Exception as exc:  # pydantic ValidationError, with every field problem
            errors.append(f"{_where(name, lineno)} {raw.get('id')}: {exc}")
    assert not errors, "\n".join(errors)


def test_unique_ids():
    counts = Counter(raw["id"] for _, _, raw in ROWS)
    dupes = sorted(i for i, n in counts.items() if n > 1)
    assert not dupes, f"duplicate ids: {dupes}"


def test_category_enum():
    allowed = {c.value for c in Category}
    bad = [raw["id"] for _, _, raw in ROWS if raw.get("category") not in allowed]
    assert not bad, f"categories outside the enum: {bad}"
    assert {raw["nature"] for _, _, raw in ROWS} <= {n.value for n in Nature}


def test_date_is_trading_day():
    bad = [
        f"{e.id} {e.date} ({e.date:%A})"
        for e in _events()
        if not trading_calendar.is_trading_day(e.date)
    ]
    assert not bad, "dates that are not NYSE trading days:\n" + "\n".join(bad)


def test_split_matches_date():
    bad = [e.id for e in _events() if e.split != split_for(e.date)]
    assert not bad, f"split does not match date: {bad}"
    # Boundary sanity: the holdout starts on 2023-01-01.
    assert split_for(date(2022, 12, 30)) == Split.DEV
    assert split_for(date(2023, 1, 3)) == Split.HOLDOUT


def test_file_matches_years_and_drafter():
    bad = []
    for name, lineno, raw in ROWS:
        first, last, tool = FILE_RULES[name]
        year = int(raw["date"][:4])
        if not first <= year <= last:
            bad.append(f"{_where(name, lineno)} {raw['id']}: year {year} outside {first}-{last}")
        if raw["drafted_by"] != tool.value:
            bad.append(f"{_where(name, lineno)} {raw['id']}: drafted_by {raw['drafted_by']}, expected {tool.value}")
    assert not bad, "\n".join(bad)


def test_source_url_and_quote_present():
    bad = []
    for e in _events():
        if not e.source_url.startswith("https://"):
            bad.append(f"{e.id}: source_url is not https")
        if len(e.source_quote.strip()) < 40:
            bad.append(f"{e.id}: source_quote shorter than 40 characters")
    assert not bad, "\n".join(bad)


def test_trigger_has_no_outcome_words():
    bad = []
    for e in _events():
        if m := OUTCOME_RE.search(e.trigger):
            bad.append(f"{e.id}: outcome word {m.group(0)!r}")
        if m := PERCENT_RE.search(e.trigger):
            bad.append(f"{e.id}: percentage {m.group(0)!r}")
    assert not bad, "\n".join(bad)


def test_trigger_has_no_future_reference():
    bad = [f"{e.id}: {m.group(0)!r}" for e in _events() if (m := FUTURE_RE.search(e.trigger))]
    assert not bad, "\n".join(bad)


def test_outcome_word_checks_catch_examples():
    assert OUTCOME_RE.search("Stocks plunged after the announcement")
    assert PERCENT_RE.search("Oil jumps 5% on the news")
    assert PERCENT_RE.search("a 25 percent tariff")
    assert FUTURE_RE.search("The bank would go on to fail")
    assert not OUTCOME_RE.search("The Fed lowers its target range by a quarter point")


def test_verified_by_differs_from_drafted_by():
    bad = [e.id for e in _events() if e.verified_by is not None and e.verified_by == e.drafted_by]
    assert not bad, f"self-verified events: {bad}"


def test_category_coverage():
    names = {p.name for p in FILES}
    if names != set(FILE_RULES):
        pytest.skip("coverage is checked once both event files are merged")
    events = _events()
    per_category = Counter(e.category for e in events)
    thin = {c.value: per_category.get(c, 0) for c in Category if per_category.get(c, 0) < MIN_PER_CATEGORY}
    assert not thin, f"categories with fewer than {MIN_PER_CATEGORY} events: {thin}"
    favorable = sum(e.nature == Nature.FAVORABLE for e in events)
    assert favorable >= MIN_FAVORABLE, f"only {favorable} favorable events"


def test_verified_before_build():
    if os.getenv("SCENARIO_REQUIRE_VERIFIED") != "1":
        pytest.skip("set SCENARIO_REQUIRE_VERIFIED=1 to require cross-verification")
    unverified = [e.id for e in _events() if e.verified_by is None]
    assert not unverified, f"unverified events: {unverified}"


def _trading_days_between(a: date, b: date) -> int:
    """Number of trading-day steps from a to b (a <= b, both trading days)."""
    steps, day = 0, a
    while day < b:
        day = trading_calendar.add_trading_days(day, 1)
        steps += 1
    return steps


def _unflagged_pairs(events: list[Event]) -> list[str]:
    """Same-category events within CLUSTER_WINDOW trading days that do not share a cluster_id."""
    events = sorted(events, key=lambda e: (e.date, e.id))
    problems = []
    for i, first in enumerate(events):
        for second in events[i + 1:]:
            if (second.date - first.date).days > 20:
                break  # 10 trading days never span more than 20 calendar days
            if second.category != first.category:
                continue
            if _trading_days_between(first.date, second.date) > CLUSTER_WINDOW:
                continue
            if first.cluster_id is None or first.cluster_id != second.cluster_id:
                problems.append(
                    f"{first.id} ({first.date}) and {second.id} ({second.date}) are both "
                    f"{first.category.value} within {CLUSTER_WINDOW} trading days but do not share a cluster_id"
                )
    return problems


def test_clusters_flagged():
    problems = _unflagged_pairs(_events())
    assert not problems, "\n".join(problems)


def test_cluster_rule_detects_unflagged_pair():
    if not ROWS:
        pytest.skip("no events")
    base = ROWS[0][2]
    def make(event_id, day, cluster):
        return Event.model_validate(
            {**base, "id": event_id, "date": day, "split": "dev", "verified_by": None, "cluster_id": cluster}
        )
    near = [make("synthetic-a", "2020-03-02", None), make("synthetic-b", "2020-03-16", None)]  # 10 trading days
    assert len(_unflagged_pairs(near)) == 1
    shared = [make("synthetic-a", "2020-03-02", "x"), make("synthetic-b", "2020-03-16", "x")]
    assert _unflagged_pairs(shared) == []
    far = [make("synthetic-a", "2020-03-02", None), make("synthetic-b", "2020-03-17", None)]  # 11 trading days
    assert _unflagged_pairs(far) == []
