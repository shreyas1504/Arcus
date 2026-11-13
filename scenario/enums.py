"""Fixed vocabularies and constants shared by every Scenario Lab module.

Changing anything here changes the contract (PLAN.md Step 0): update the schemas,
the frontend fixture and STATUS.md in the same commit.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum


class Category(StrEnum):
    GEOPOLITICAL_CONFLICT = "geopolitical_conflict"
    TERRORISM = "terrorism"
    TRADE_TARIFFS = "trade_tariffs"
    MONETARY_POLICY = "monetary_policy"
    FISCAL_DEBT = "fiscal_debt"
    FINANCIAL_CREDIT = "financial_credit"
    ENERGY_OIL = "energy_oil"
    PANDEMIC_HEALTH = "pandemic_health"
    DISASTER_SUPPLY = "disaster_supply"
    TECH_SECTOR = "tech_sector"
    ELECTION_POLITICAL = "election_political"


class Nature(StrEnum):
    """Judged from the cause (a rate cut, a ceasefire), never from the market move."""

    ADVERSE = "adverse"
    FAVORABLE = "favorable"


class Onset(StrEnum):
    SUDDEN = "sudden"
    GRADUAL = "gradual"


class Region(StrEnum):
    US = "us"
    CANADA = "canada"
    LATIN_AMERICA = "latin_america"
    EUROPE = "europe"
    UK = "uk"
    RUSSIA_UKRAINE = "russia_ukraine"
    MIDDLE_EAST = "middle_east"
    AFRICA = "africa"
    CHINA = "china"
    TAIWAN = "taiwan"
    JAPAN = "japan"
    KOREA = "korea"
    INDIA = "india"
    SOUTHEAST_ASIA = "southeast_asia"
    AUSTRALIA = "australia"
    EMERGING_MARKETS = "emerging_markets"
    GLOBAL = "global"


class Sector(StrEnum):
    TECHNOLOGY = "technology"
    FINANCIALS = "financials"
    ENERGY = "energy"
    HEALTH_CARE = "health_care"
    INDUSTRIALS = "industrials"
    CONSUMER_DISCRETIONARY = "consumer_discretionary"
    CONSUMER_STAPLES = "consumer_staples"
    UTILITIES = "utilities"
    MATERIALS = "materials"
    SEMICONDUCTORS = "semiconductors"
    BROAD = "broad"


class Severity(StrEnum):
    MILD = "mild"  # 25th percentile of precedent outcomes (less bad)
    TYPICAL = "typical"  # weighted median
    SEVERE = "severe"  # 10th percentile (90th-percentile loss)


SEVERITY_QUANTILE: dict[Severity, float] = {
    Severity.MILD: 0.75,
    Severity.TYPICAL: 0.50,
    Severity.SEVERE: 0.10,
}


class Confidence(StrEnum):
    NORMAL = "normal"
    LOW = "low"  # no precedent above the backtest-chosen similarity threshold


class ImpactSource(StrEnum):
    ACTUAL = "actual"  # the stock had prices across the precedent window
    ESTIMATED = "estimated"  # factor-model estimate
    ESTIMATED_LOW_HISTORY = "estimated_low_history"  # factor estimate from < MIN_FACTOR_OBS days


class Split(StrEnum):
    DEV = "dev"
    HOLDOUT = "holdout"


class Tool(StrEnum):
    CLAUDE = "claude"
    CURSOR = "cursor"


HOLDOUT_START = date(2023, 1, 1)


def split_for(day: date) -> Split:
    return Split.HOLDOUT if day >= HOLDOUT_START else Split.DEV


# Horizons, in trading days. Paths are indexed t = 0..N where t = 0 is the close on
# day -1 (value 0.0) and t = k is the close of the k-th trading day starting with day 0.
HORIZON_DAYS = 21
PATH_DAYS = 63
RECOVERY_DAYS = 504
TOP_K = 5
RANGE_LEVEL = 0.80

# Factor columns, in this order everywhere (library arrays, factor history, betas).
# ETFs and Brent are daily simple returns; DGS10_CHG is the daily change of the
# 10-year Treasury yield in percentage points.
FACTOR_SPY = "SPY"
FACTOR_RATES = "DGS10_CHG"
FACTOR_OIL = "BRENT"
FACTOR_SEMIS = "SOXX"

SECTOR_ETF: dict[Sector, str] = {
    Sector.TECHNOLOGY: "XLK",
    Sector.FINANCIALS: "XLF",
    Sector.ENERGY: "XLE",
    Sector.HEALTH_CARE: "XLV",
    Sector.INDUSTRIALS: "XLI",
    Sector.CONSUMER_DISCRETIONARY: "XLY",
    Sector.CONSUMER_STAPLES: "XLP",
    Sector.UTILITIES: "XLU",
    Sector.MATERIALS: "XLB",
    Sector.SEMICONDUCTORS: "XLK",  # plus FACTOR_SEMIS as an extra factor
    Sector.BROAD: FACTOR_SPY,
}

FACTOR_NAMES: tuple[str, ...] = (
    FACTOR_SPY,
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB",
    FACTOR_SEMIS,
    FACTOR_RATES,
    FACTOR_OIL,
)

# yfinance `info["sector"]` / `info["industry"]` values mapped onto Sector.
YF_SECTOR_TO_SECTOR: dict[str, Sector] = {
    "Technology": Sector.TECHNOLOGY,
    "Financial Services": Sector.FINANCIALS,
    "Energy": Sector.ENERGY,
    "Healthcare": Sector.HEALTH_CARE,
    "Industrials": Sector.INDUSTRIALS,
    "Consumer Cyclical": Sector.CONSUMER_DISCRETIONARY,
    "Consumer Defensive": Sector.CONSUMER_STAPLES,
    "Utilities": Sector.UTILITIES,
    "Basic Materials": Sector.MATERIALS,
    "Real Estate": Sector.BROAD,
    "Communication Services": Sector.BROAD,
}
SEMICONDUCTOR_INDUSTRIES = frozenset({"Semiconductors", "Semiconductor Equipment & Materials"})


def sector_from_yfinance(sector: str | None, industry: str | None = None) -> Sector:
    if industry in SEMICONDUCTOR_INDUSTRIES:
        return Sector.SEMICONDUCTORS
    return YF_SECTOR_TO_SECTOR.get(sector or "", Sector.BROAD)
