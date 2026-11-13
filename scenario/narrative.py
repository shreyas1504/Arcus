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
from scenario.schemas import PortfolioOutcome, ScenarioReplay, WhatIfResponse, WhatIfResponseV2

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
        if low == 0 and high == 0:
            sentences.append("Some precedents never fell below their start.")
        elif low == 0:
            sentences.append(
                f"Some precedents never fell below their start; the longest took {high} trading days."
            )
        elif low == high:
            sentences.append(f"Regaining the starting value took {low} trading days.")
        else:
            sentences.append(
                f"Regaining the starting value took between {low} and {high} trading days."
            )
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


LOW_CONFIDENCE_V2 = (
    "There is no close precedent for this scenario, so only the crisis replay is shown."
)
LIMITS_V2 = (
    "Arcus cannot predict whether or when a crisis happens; each replay shows what "
    "happened, applied to today's holdings, not a forecast."
)


def _top_driver_names(replay: ScenarioReplay, *, limit: int = 2) -> tuple[list[str], str]:
    """Top contributors for the portfolio move: positive when up, negative when down.

    Returns (tickers, kind) where kind is "gain", "loss", or "" if there is no signed driver.
    """
    port = replay.portfolio_return_21d
    if port > 0:
        candidates = [h for h in replay.holdings if h.contribution > 0]
        candidates.sort(key=lambda h: (-h.contribution, h.ticker))
        return [h.ticker for h in candidates[:limit]], "gain"
    if port < 0:
        candidates = [h for h in replay.holdings if h.contribution < 0]
        candidates.sort(key=lambda h: (h.contribution, h.ticker))
        return [h.ticker for h in candidates[:limit]], "loss"
    return [], ""


def _scenario_sentence(replay: ScenarioReplay) -> str:
    year = replay.date.year
    moved = _pct(replay.portfolio_return_21d)
    drivers, kind = _top_driver_names(replay)
    if drivers and kind:
        who = " and ".join(drivers)
        return (
            f"If it plays out like {replay.name} ({year}), this portfolio moved {moved}; "
            f"{who} drove most of the {kind}."
        )
    return f"If it plays out like {replay.name} ({year}), this portfolio moved {moved}."


def _span_sentence(response: WhatIfResponseV2) -> str | None:
    if not response.scenarios or response.span_low is None or response.span_high is None:
        return None
    n = len(response.scenarios)
    shocks = "shock" if n == 1 else "shocks"
    return (
        f"Across these {n} past {shocks} this portfolio moved between "
        f"{_pct(response.span_low)} and {_pct(response.span_high)}."
    )


def _resilience_sentence(response: WhatIfResponseV2) -> str | None:
    r = response.resilience
    if r is None or r.crises_total == 0:
        return None
    sentence = (
        f"This portfolio fell more than the S&P in {r.worse_than_sp500} of "
        f"{r.crises_total} crises."
    )
    if r.top_drivers:
        who = " and ".join(r.top_drivers)
        sentence += f" {who} drove most of the damage."
    return sentence


def render_v2(response: WhatIfResponseV2) -> str:
    """Narrative for a v2 (stress-test) response whose `narrative` is still empty (PLAN v2).

    Contract stub from C4b-contract; Cursor implements it in U4b. Must contain: one sentence
    per scenario replay ("If it plays out like <name> (<year>), this portfolio moved X%;
    <top tickers> drove most of it"), the span sentence when there are scenarios, the
    resilience sentence when there are crises, the low-confidence sentence when confidence
    is LOW, and the limits sentence (past shocks applied to today's holdings, not a
    forecast). Every number must be one of the response's own values, formatted; no advice
    words.
    """
    sentences: list[str] = []
    if response.confidence == Confidence.LOW:
        sentences.append(LOW_CONFIDENCE_V2)
    for replay in response.scenarios:
        sentences.append(_scenario_sentence(replay))
    span = _span_sentence(response)
    if span:
        sentences.append(span)
    resilience = _resilience_sentence(response)
    if resilience:
        sentences.append(resilience)
    sentences.append(LIMITS_V2)
    return " ".join(sentences)
