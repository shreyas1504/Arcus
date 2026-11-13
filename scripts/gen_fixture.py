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
    BacktestSummary,
    HoldingImpact,
    ParsedScenario,
    PathSeries,
    PortfolioOutcome,
    Precedent,
    WhatIfResponse,
)

OUT = Path(__file__).resolve().parent.parent / "frontend/src/lib/__fixtures__/whatif-response.json"
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


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(build(), indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
