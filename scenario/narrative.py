"""Template narrative (PLAN.md 3d).

Fills a fixed template using only values already in the response. Every number in
the text must appear in the response fields (formatted). No model call, no advice
words. A low-confidence response gets the "no close precedent" sentence.

Spans that would otherwise need a derived number are written in words: the 63-day
drawdown window is "the following three months" and the 504-day recovery horizon is
"two years". Precedent counts, names and dates are left to the page.
"""

from __future__ import annotations

from scenario.enums import Confidence, Severity
from scenario.schemas import PortfolioOutcome, WhatIfResponse

LOW_CONFIDENCE = (
    "There is no close precedent for this scenario, so these figures use every past "
    "shock in the library with equal weight and the range is wider than usual."
)
NO_DATA = "There is not enough price history for these holdings to estimate an outcome."

_SEVERITY_LABEL = {
    Severity.TYPICAL: "typical",
    Severity.MILD: "mild-case",
    Severity.SEVERE: "severe-case",
}


def _pct(value: float) -> str:
    text = f"{value * 100:.1f}"
    return f"{'0.0' if text == '-0.0' else text}%"


def _outcome(p: PortfolioOutcome) -> list[str]:
    sentences = [
        f"In the past shocks most similar to this scenario, this portfolio's "
        f"{_SEVERITY_LABEL[p.severity]} {p.horizon_days}-day return was {_pct(p.typical_return)}, "
        f"with an {p.range_level * 100:.0f}% range of {_pct(p.range_low)} to {_pct(p.range_high)}.",
        f"The worst drawdown in the following three months was {_pct(p.worst_drawdown_63d)}.",
    ]
    low, high = p.recovery_days_low, p.recovery_days_high
    if low is not None and high is not None:
        span = f"{low} trading days" if low == high else f"between {low} and {high} trading days"
        sentences.append(f"Regaining the starting value took {span}.")
    if p.unrecovered_share > 0:
        sentences.append(
            f"{_pct(p.unrecovered_share)} of those precedents had not regained it within two years."
        )
    return sentences


def render(response: WhatIfResponse) -> str:
    """Return the narrative for a response whose `narrative` field is still empty."""
    sentences: list[str] = []
    if response.confidence == Confidence.LOW:
        sentences.append(LOW_CONFIDENCE)
    if response.portfolio is None:
        sentences.append(NO_DATA)
    else:
        sentences.extend(_outcome(response.portfolio))
    sentences.append("Past shocks are a guide to exposure, not a forecast.")
    return " ".join(sentences)
