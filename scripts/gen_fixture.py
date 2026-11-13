"""Generate the synthetic WhatIfResponse fixture the frontend is built against.

Everything here is clearly fake: tickers DEMO1/DEMO2, events named "Example ...",
example.com links. The numbers are made internally consistent (weights, quantiles,
contributions) so UI tests behave like the real engine's output.

    python scripts/gen_fixture.py
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from scenario.enums import Category, Confidence, ImpactSource, Nature, Sector, Severity
from scenario.schemas import (
    WhatIfResponseV2,
    BacktestSummary,
    HoldingImpact,
    ParsedScenario,
    PathSeries,
    PortfolioOutcome,
    Precedent,
    WhatIfResponse,
)

OUT = Path(__file__).resolve().parent.parent / "frontend/src/lib/__fixtures__/whatif-response.json"
OUT_V2 = OUT.with_name("whatif-response-v2.json")
Q_HAT = 1.6  # synthetic

HOLDINGS = {"DEMO1": (0.6, Sector.SEMICONDUCTORS), "DEMO2": (0.4, Sector.UTILITIES)}
# (id, name, date, category, nature, similarity, score, sp500 21d, {ticker: (21d return, source)})
EVENTS = [
    ("example-blockade-drill", "Example: naval blockade drill", date(2022, 8, 2),
     Category.GEOPOLITICAL_CONFLICT, Nature.ADVERSE, 0.82, 0.87, -0.031,
     {"DEMO1": (-0.092, ImpactSource.ACTUAL), "DEMO2": (0.004, ImpactSource.ACTUAL)}),
    ("example-export-ban", "Example: chip export ban", date(2019, 5, 13),
     Category.TRADE_TARIFFS, Nature.ADVERSE, 0.74, 0.74, -0.048,
     {"DEMO1": (-0.135, ImpactSource.ACTUAL), "DEMO2": (0.012, ImpactSource.ESTIMATED)}),
    ("example-strait-incident", "Example: shipping strait incident", date(2011, 3, 14),
     Category.DISASTER_SUPPLY, Nature.ADVERSE, 0.66, 0.66, -0.012,
     {"DEMO1": (-0.041, ImpactSource.ESTIMATED), "DEMO2": (-0.006, ImpactSource.ESTIMATED)}),
]


def lower_weighted_quantile(values: list[float], weights: list[float], q: float) -> float:
    pairs = sorted(zip(values, weights))
    total = sum(weights)
    cumulative = 0.0
    for value, weight in pairs:
        cumulative += weight / total
        if cumulative >= q - 1e-12:
            return value
    return pairs[-1][0]


def path(final_21d: float, trough: float) -> list[float | None]:
    """A smooth synthetic 64-point path: dips to `trough` by t=15, ends near final at t=21, recovers by t=63."""
    values: list[float | None] = [0.0]
    for t in range(1, 64):
        if t <= 15:
            v = trough * t / 15
        elif t <= 21:
            v = trough + (final_21d - trough) * (t - 15) / 6
        else:
            v = final_21d + (0.01 - final_21d) * (t - 21) / 42
        values.append(round(v, 5))
    return values


def build() -> dict:
    scores = [e[6] for e in EVENTS]
    weights = [s / sum(scores) for s in scores]
    port = [sum(HOLDINGS[t][0] * e[8][t][0] for t in HOLDINGS) for e in EVENTS]

    median = lower_weighted_quantile(port, weights, 0.5)
    mean = sum(w * r for w, r in zip(weights, port))
    spread = max(lower_weighted_quantile([abs(r - median) for r in port], weights, 0.5), 0.005)
    troughs = [r * 1.4 for r in port]
    drawdowns = [min(t, r) for t, r in zip(troughs, port)]

    holdings = []
    for ticker, (weight, sector) in HOLDINGS.items():
        ret = sum(w * e[8][ticker][0] for w, e in zip(weights, EVENTS))
        actual = sum(w for w, e in zip(weights, EVENTS) if e[8][ticker][1] is ImpactSource.ACTUAL)
        holdings.append(
            HoldingImpact(
                ticker=ticker,
                weight=weight,
                sector=sector,
                return_21d=round(ret, 6),
                contribution=round(weight * ret, 6),
                source=ImpactSource.ACTUAL if actual >= 0.5 else ImpactSource.ESTIMATED,
                actual_share=round(actual, 6),
            )
        )

    response = WhatIfResponse(
        scenario="What if China blockades Taiwan?",
        parsed=ParsedScenario(
            category=Category.GEOPOLITICAL_CONFLICT,
            regions=["china", "taiwan"],
            sectors=[Sector.SEMICONDUCTORS],
            companies=[],
            search_text="China naval blockade of Taiwan disrupts shipping and chip supply",
        ),
        as_of=date(2026, 11, 13),
        severity=Severity.TYPICAL,
        confidence=Confidence.NORMAL,
        precedents=[
            Precedent(
                event_id=e[0], name=e[1], date=e[2], category=e[3], nature=e[4],
                trigger=f"{e[1].removeprefix('Example: ').capitalize()} is announced (synthetic example).",
                similarity=e[5], weight=round(w, 6), sp500_return_21d=e[7],
                portfolio_return_21d=round(r, 6), source_url=f"https://example.com/{e[0]}",
            )
            for e, w, r in zip(EVENTS, weights, port)
        ],
        portfolio=PortfolioOutcome(
            severity=Severity.TYPICAL,
            typical_return=round(median, 6),
            median_return=round(median, 6),
            mean_return=round(sum(h.contribution for h in holdings), 6),
            range_low=round(median - Q_HAT * spread, 6),
            range_high=round(median + Q_HAT * spread, 6),
            worst_drawdown_63d=round(lower_weighted_quantile(drawdowns, weights, 0.5), 6),
            recovery_days_low=34,
            recovery_days_high=118,
            unrecovered_share=0.0,
        ),
        holdings=holdings,
        skipped=[],
        paths=[
            PathSeries(event_id=e[0], label=f"{e[1]} ({e[2].isoformat()})", values=path(r, t))
            for e, r, t in zip(EVENTS, port, troughs)
        ],
        narrative=(
            "Example only. In the 3 closest precedents, this portfolio's typical 21-day "
            f"return was {median:.1%}, with an 80% range of {median - Q_HAT * spread:.1%} "
            f"to {median + Q_HAT * spread:.1%}."
        ),
        backtest=BacktestSummary(available=False),
        remaining_today=19,
    )
    assert abs(mean - response.portfolio.mean_return) < 1e-5
    return json.loads(response.model_dump_json())


# --------------------------------------------------------------------------- v2 (stress test)

V2_HOLDINGS = {"DEMO1": (0.5, Sector.SEMICONDUCTORS), "DEMO2": (0.3, Sector.UTILITIES), "DEMO3": (0.2, Sector.FINANCIALS)}
# (id, name, date, category, nature, similarity or None, spx 21d, spx dd63,
#  {ticker: (21d return, source, recovery_days)}, portfolio recovery, known, recovery_source)
V2_SCENARIOS = [
    ("example-strait-closure", "Example: strait closure", date(2019, 5, 13), Category.TRADE_TARIFFS, Nature.ADVERSE,
     0.71, -0.048, -0.066,
     {"DEMO1": (-0.142, ImpactSource.ACTUAL, 41), "DEMO2": (0.012, ImpactSource.ACTUAL, 0), "DEMO3": (-0.031, ImpactSource.ACTUAL, 18)},
     41, True, "actual"),
    ("example-border-clash", "Example: border clash", date(2010, 11, 23), Category.GEOPOLITICAL_CONFLICT, Nature.ADVERSE,
     0.64, -0.021, -0.034,
     {"DEMO1": (-0.051, ImpactSource.ESTIMATED, 22), "DEMO2": (0.004, ImpactSource.ACTUAL, 0), "DEMO3": (-0.018, ImpactSource.ACTUAL, 9)},
     22, True, "mixed"),
    ("example-port-quake", "Example: port earthquake", date(2024, 4, 3), Category.DISASTER_SUPPLY, Nature.ADVERSE,
     0.58, -0.036, -0.055,
     {"DEMO1": (-0.071, ImpactSource.ACTUAL, 15), "DEMO2": (-0.006, ImpactSource.ACTUAL, 7), "DEMO3": (-0.012, ImpactSource.ACTUAL, 6)},
     15, True, "actual"),
]
V2_CRISES = [
    ("example-bank-collapse", "Example: bank collapse", date(2008, 9, 15), Category.FINANCIAL_CREDIT, Nature.ADVERSE,
     None, -0.192, -0.281,
     {"DEMO1": (-0.262, ImpactSource.ESTIMATED, None), "DEMO2": (-0.084, ImpactSource.ACTUAL, 120), "DEMO3": (-0.301, ImpactSource.ACTUAL, None)},
     None, True, "mixed"),
    ("example-pandemic-crash", "Example: pandemic crash", date(2020, 3, 11), Category.PANDEMIC_HEALTH, Nature.ADVERSE,
     None, -0.044, -0.262,
     {"DEMO1": (-0.031, ImpactSource.ACTUAL, 58), "DEMO2": (-0.075, ImpactSource.ACTUAL, 190), "DEMO3": (-0.112, ImpactSource.ACTUAL, 240)},
     96, True, "actual"),
]


def _replay(row) -> dict:
    (event_id, name, day, category, nature, similarity, spx, spx_dd, per, recovery, known, source) = row
    holdings = []
    for ticker, (weight, sector) in V2_HOLDINGS.items():
        ret, src, rec = per[ticker]
        holdings.append({
            "ticker": ticker, "weight": weight, "sector": sector.value, "return_21d": ret,
            "contribution": round(weight * ret, 6), "source": src.value, "recovery_days": rec,
        })
    total = round(sum(h["contribution"] for h in holdings), 6)
    trough = round(min(total * 1.35, total), 6)
    path = [0.0] + [round(trough * t / 12, 6) for t in range(1, 13)]
    path += [round(trough + (total - trough) * (t - 12) / 9, 6) for t in range(13, 22)]
    path += [round(total + (0.01 - total) * (t - 21) / 42, 6) for t in range(22, 64)]
    return {
        "event_id": event_id, "name": name, "date": day.isoformat(), "category": category.value,
        "nature": nature.value, "trigger": f"{name.removeprefix('Example: ').capitalize()} is announced (synthetic example).",
        "similarity": similarity, "source_url": f"https://example.com/{event_id}",
        "portfolio_return_21d": total, "sp500_return_21d": spx,
        "worst_drawdown_63d": round(min(0.0, trough * 1.05), 6), "sp500_worst_drawdown_63d": spx_dd,
        "recovery_days": recovery, "recovery_known": known, "recovery_source": source,
        "path": path, "holdings": holdings,
    }


def exposure_rule(replays: list[dict]) -> list[dict]:
    """engine.exposure_ranking's documented rule, on plain dicts (fixture only)."""
    contrib: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for replay in replays:
        rows = sorted(replay["holdings"], key=lambda h: (h["contribution"], h["ticker"]))
        if rows[0]["contribution"] < 0:
            counts[rows[0]["ticker"]] = counts.get(rows[0]["ticker"], 0) + 1
        for h in replay["holdings"]:
            contrib.setdefault(h["ticker"], []).append(h["contribution"])
    out = [
        {"ticker": t, "mean_contribution": round(sum(v) / len(v), 6), "most_exposed_count": counts.get(t, 0), "scenarios": len(v)}
        for t, v in contrib.items()
    ]
    return sorted(out, key=lambda r: (r["mean_contribution"], r["ticker"]))


def resilience_rule(crises: list[dict]) -> dict:
    """engine.resilience_summary's documented rule, on plain dicts (fixture only)."""
    with_spx = [c for c in crises if c["sp500_worst_drawdown_63d"] is not None]
    worse = sum(c["worst_drawdown_63d"] < c["sp500_worst_drawdown_63d"] for c in with_spx)
    ranked = sorted((r for r in exposure_rule(crises) if r["most_exposed_count"] > 0),
                    key=lambda r: (-r["most_exposed_count"], r["mean_contribution"], r["ticker"]))
    return {"worse_than_sp500": worse, "crises_total": len(with_spx), "top_drivers": [r["ticker"] for r in ranked[:2]]}


def build_v2() -> dict:
    scenarios = [_replay(r) for r in V2_SCENARIOS]
    crises = [_replay(r) for r in V2_CRISES]
    returns = [s["portfolio_return_21d"] for s in scenarios]
    response = {
        "scenario": "What if China blockades Taiwan?",
        "parsed": {"category": "geopolitical_conflict", "nature": "adverse", "regions": ["china", "taiwan"],
                   "sectors": ["semiconductors"], "companies": [],
                   "search_text": "China naval blockade of Taiwan disrupts shipping and chip supply", "fallback": False},
        "as_of": "2026-11-13",
        "confidence": "normal",
        "scenarios": scenarios,
        "span_low": min(returns),
        "span_high": max(returns),
        "exposure": exposure_rule(scenarios),
        "crises": crises,
        "resilience": resilience_rule(crises),
        "skipped": [],
        "narrative": (
            f"Example only. If it plays out like the strait closure, this portfolio moved {returns[0]:.1%}. "
            f"Across these 3 past shocks it moved between {min(returns):.1%} and {max(returns):.1%}. "
            "Past shocks applied to today's holdings, not a forecast."
        ),
        # Holdout gate v2 numbers from scenario/eval/calibration.json (C5), rounded for the fixture.
        "backtest": {
            "available": True,
            "holdout_events": 32,
            "h1_mae": {"value": 0.0163, "ci_low": 0.0153, "ci_high": 0.0173},
            "h1_mae_baseline": {"value": 0.0215, "ci_low": 0.0195, "ci_high": 0.0237},
            "h2_rank": {"value": 0.467, "ci_low": 0.423, "ci_high": 0.512},
            "h3_drawdown_mae": {"value": 0.0154, "ci_low": 0.0142, "ci_high": 0.0165},
            "h3_drawdown_mae_baseline": {"value": 0.02, "ci_low": 0.018, "ci_high": 0.0219},
            "h4_within_one_bucket": {"value": 0.931, "ci_low": 0.905, "ci_high": 0.953},
            "h4_exact_bucket": {"value": 0.705, "ci_low": 0.66, "ci_high": 0.748},
            "h4_exact_bucket_baseline": {"value": 0.594, "ci_low": 0.514, "ci_high": 0.667},
            "gate_passed": True,
            "recovery_shown_from": "all",
            "results_url": None,
        },
        "remaining_today": 19,
    }
    return json.loads(WhatIfResponseV2.model_validate(response).model_dump_json())


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n")
    OUT_V2.write_text(json.dumps(build_v2(), indent=2) + "\n")
    print(f"wrote {OUT} and {OUT_V2}")


if __name__ == "__main__":
    main()
