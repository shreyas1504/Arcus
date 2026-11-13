"""Tests for scenario/narrative.py, by Claude from PLAN 3d (owned by Claude; Cursor must
not edit them; disputes go to STATUS.md).

Not strictly blind: the implementation was shown to Claude in an automatic file-change
notice before these were written. They therefore test the plan's rules, not wording:
  - every number in the text is one of the response's own values, formatted
  - no advice words
  - a low-confidence response says there is no close precedent
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scenario.enums import Confidence, Severity
from scenario.narrative import render
from scenario.schemas import WhatIfResponse

FIXTURE = Path(__file__).resolve().parents[2] / "frontend/src/lib/__fixtures__/whatif-response.json"
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
ADVICE_RE = re.compile(r"\b(buy|sell|should|recommend\w*|guarantee\w*|must|advise\w*)\b", re.IGNORECASE)


def _base(**portfolio_updates) -> WhatIfResponse:
    response = WhatIfResponse.model_validate(json.loads(FIXTURE.read_text())).model_copy(update={"narrative": ""})
    if portfolio_updates:
        portfolio = response.portfolio.model_copy(update=portfolio_updates)
        response = response.model_copy(update={"portfolio": portfolio})
    return response


def _allowed_numbers(response: WhatIfResponse) -> set[str]:
    allowed: set[str] = set()
    p = response.portfolio
    if p is None:
        return allowed
    for value in (
        p.typical_return, p.median_return, p.mean_return, p.range_low, p.range_high,
        p.worst_drawdown_63d, p.unrecovered_share, p.range_level,
    ):
        for scaled in (value * 100, abs(value * 100)):
            allowed |= {f"{scaled:.1f}", f"{scaled:.0f}", f"{scaled:.2f}"}
    for value in (p.horizon_days, p.recovery_days_low, p.recovery_days_high):
        if value is not None:
            allowed.add(str(value))
    return allowed


def _numbers(text: str) -> list[str]:
    return NUMBER_RE.findall(text)


@pytest.mark.parametrize("severity", list(Severity))
def test_every_number_traceable(severity):
    response = _base(severity=severity)
    text = render(response)
    allowed = _allowed_numbers(response)
    assert _numbers(text), "the narrative should state the computed outcome"
    stray = [n for n in _numbers(text) if n not in allowed]
    assert stray == [], f"numbers not in the response: {stray}"


def test_unrecovered_share_is_traceable():
    response = _base(unrecovered_share=0.4, recovery_days_low=None, recovery_days_high=None)
    text = render(response)
    stray = [n for n in _numbers(text) if n not in _allowed_numbers(response)]
    assert stray == []


def test_no_advice_words():
    for confidence in Confidence:
        text = render(_base().model_copy(update={"confidence": confidence}))
        assert not ADVICE_RE.search(text), text


def test_low_confidence_wording():
    text = render(_base().model_copy(update={"confidence": Confidence.LOW}))
    assert "no close precedent" in text.lower()
    normal = render(_base())
    assert "no close precedent" not in normal.lower()


def test_no_portfolio_gives_no_numbers():
    response = _base().model_copy(update={"portfolio": None, "holdings": []})
    text = render(response)
    assert text.strip()
    assert _numbers(text) == [] and "%" not in text


def test_render_is_pure_and_deterministic():
    response = _base()
    before = response.model_dump()
    assert render(response) == render(response)
    assert response.model_dump() == before
