"""Tests for scenario.narrative.render_v2 (U4b). Cursor-owned; separate from Claude's v1 tests."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scenario.enums import Confidence
from scenario.narrative import render_v2
from scenario.schemas import WhatIfResponseV2

FIXTURE = Path(__file__).resolve().parents[2] / "frontend/src/lib/__fixtures__/whatif-response-v2.json"
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
ADVICE_RE = re.compile(r"\b(buy|sell|should|recommend\w*|guarantee\w*|must|advise\w*)\b", re.IGNORECASE)


def _base(**updates) -> WhatIfResponseV2:
    response = WhatIfResponseV2.model_validate(json.loads(FIXTURE.read_text()))
    return response.model_copy(update={"narrative": "", **updates}, deep=True)


def _allowed_numbers(response: WhatIfResponseV2) -> set[str]:
    allowed: set[str] = set()
    for value in (response.span_low, response.span_high):
        if value is not None:
            for scaled in (value * 100, abs(value * 100)):
                allowed |= {f"{scaled:.1f}", f"{scaled:.0f}", f"{scaled:.2f}"}
                text = f"{scaled:.1f}"
                allowed.add("0.0" if text == "-0.0" else text)
    for replay in list(response.scenarios) + list(response.crises):
        allowed.add(str(replay.date.year))
        for value in (replay.portfolio_return_21d, replay.worst_drawdown_63d):
            for scaled in (value * 100, abs(value * 100)):
                text = f"{scaled:.1f}"
                allowed.add("0.0" if text == "-0.0" else text)
                allowed |= {f"{scaled:.0f}", f"{scaled:.2f}"}
        for holding in replay.holdings:
            for value in (holding.return_21d, holding.contribution, holding.weight):
                for scaled in (value * 100, abs(value * 100)):
                    text = f"{scaled:.1f}"
                    allowed.add("0.0" if text == "-0.0" else text)
    if response.resilience is not None:
        allowed.add(str(response.resilience.worse_than_sp500))
        allowed.add(str(response.resilience.crises_total))
    allowed.add(str(len(response.scenarios)))
    return allowed


def test_every_number_traceable():
    response = _base()
    text = render_v2(response)
    stray = [n for n in NUMBER_RE.findall(text) if n not in _allowed_numbers(response)]
    assert stray == [], f"numbers not in the response: {stray}\ntext={text}"


def test_no_advice_words():
    for confidence in Confidence:
        text = render_v2(_base(confidence=confidence))
        assert not ADVICE_RE.search(text), text


def test_limits_sentence():
    text = render_v2(_base())
    assert "today's holdings" in text
    assert "not a forecast" in text


def test_per_scenario_and_span_sentences():
    text = render_v2(_base())
    assert "If it plays out like Example: strait closure (2019)" in text
    assert "If it plays out like Example: border clash (2010)" in text
    assert "If it plays out like Example: port earthquake (2024)" in text
    assert "Across these 3 past shocks this portfolio moved between" in text
    assert "-7.4%" in text and "-2.8%" in text


def test_resilience_sentence():
    text = render_v2(_base())
    assert "fell more than the S&P in 1 of 2 crises" in text
    assert "DEMO1" in text


def test_low_confidence_sentence():
    low = render_v2(_base(confidence=Confidence.LOW, scenarios=[], span_low=None, span_high=None, exposure=[]))
    normal = render_v2(_base())
    assert "no close precedent" in low
    assert "no close precedent" not in normal
    assert "not a forecast" in low
