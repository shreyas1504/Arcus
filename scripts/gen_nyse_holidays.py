"""Generate scenario/nyse_holidays.json.

Past closures: weekdays with no SPY bar from 1999-01-01 to the last SPY bar
(holidays plus unscheduled closures such as 9/11 and Hurricane Sandy).
Future closures: the NYSE-published holiday list below, copied from
https://www.nyse.com/markets/hours-calendars on 2026-11-13.

    python scripts/gen_nyse_holidays.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "scenario" / "nyse_holidays.json"
START = date(1999, 1, 1)
END = date(2027, 12, 31)
SOURCE_URL = "https://www.nyse.com/markets/hours-calendars"
PUBLISHED = [
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03", "2026-05-25", "2026-06-19",
    "2026-07-03", "2026-09-07", "2026-11-26", "2026-12-25",
    "2027-01-01", "2027-01-18", "2027-02-15", "2027-03-26", "2027-05-31", "2027-06-18",
    "2027-07-05", "2027-09-06", "2027-11-25", "2027-12-24",
]


def main() -> None:
    import yfinance as yf

    bars = yf.download("SPY", start=START.isoformat(), progress=False, auto_adjust=False)
    if bars.empty:
        raise SystemExit("SPY download failed; nothing written")
    traded = {ts.date() for ts in pd.DatetimeIndex(bars.index)}
    last_bar = max(traded)

    weekdays = pd.bdate_range(START, last_bar).date
    past = sorted(d for d in weekdays if d not in traded)
    future = sorted(date.fromisoformat(d) for d in PUBLISHED if date.fromisoformat(d) > last_bar)
    # Sanity: published dates that are already past must match the SPY gaps.
    for d in PUBLISHED:
        day = date.fromisoformat(d)
        if day <= last_bar and day not in past:
            raise SystemExit(f"Published holiday {day} has an SPY bar; check the data")

    closed = past + future
    per_year = Counter(d.year for d in closed)
    for year in range(START.year, END.year + 1):
        if not 8 <= per_year[year] <= 13:
            raise SystemExit(f"{year} has {per_year[year]} closures; check the data")

    OUT.write_text(
        json.dumps(
            {
                "first_day": START.isoformat(),
                "last_day": END.isoformat(),
                "spy_history_through": last_bar.isoformat(),
                "future_source": SOURCE_URL,
                "closed": [d.isoformat() for d in closed],
            },
            indent=1,
        )
        + "\n"
    )
    print(f"wrote {len(closed)} closed days to {OUT} (SPY through {last_bar})")


if __name__ == "__main__":
    main()
