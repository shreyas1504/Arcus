"""Blind tests for scenario/factors.py (PLAN.md 3a), written from the stub docstring only.

Synthetic data with known betas; no network. Dates are business days, and as_of is
chosen so that `as_of - 3 years` is itself a row, which pins the window boundary.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from scenario import factors
from scenario.enums import FACTOR_NAMES, FACTOR_OIL, FACTOR_RATES, FACTOR_SEMIS, FACTOR_SPY, Sector

def _is_stub() -> bool:
    try:
        factors.factors_for(Sector.BROAD)
    except NotImplementedError:
        return True
    return False


# Until C2 lands, every test must fail with NotImplementedError and nothing else.
pytestmark = pytest.mark.xfail(
    _is_stub(), raises=NotImplementedError, strict=True, reason="scenario/factors.py is still the C0 stub"
)

AS_OF = date(2020, 6, 15)  # Monday
WINDOW_START = date(2017, 6, 15)  # Thursday, AS_OF minus 3 years
OLS = 1e-8  # alpha -> 0 gives ordinary least squares
SCALE = {name: 0.012 for name in FACTOR_NAMES} | {FACTOR_SPY: 0.015, FACTOR_RATES: 0.05, FACTOR_OIL: 0.02}


def make_factors(start="2016-01-01", end="2020-12-31", seed=0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(start, end)
    data = {name: rng.normal(0.0, SCALE[name], len(index)) for name in FACTOR_NAMES}
    return pd.DataFrame(data, index=index)[list(FACTOR_NAMES)]


def make_stock(f: pd.DataFrame, betas: dict[str, float], *, intercept=0.0, noise=0.002, seed=1) -> pd.Series:
    rng = np.random.default_rng(seed)
    y = intercept + sum(beta * f[name] for name, beta in betas.items())
    return y + rng.normal(0.0, noise, len(f))


def in_window(index: pd.DatetimeIndex) -> np.ndarray:
    return (index >= pd.Timestamp(WINDOW_START)) & (index < pd.Timestamp(AS_OF))


# ------------------------------------------------------------------ factors_for


def test_factors_for_follows_factor_names_order():
    assert factors.factors_for(Sector.TECHNOLOGY) == (FACTOR_SPY, "XLK", FACTOR_RATES, FACTOR_OIL)
    assert factors.factors_for(Sector.ENERGY) == (FACTOR_SPY, "XLE", FACTOR_RATES, FACTOR_OIL)
    assert factors.factors_for(Sector.SEMICONDUCTORS) == (FACTOR_SPY, "XLK", FACTOR_SEMIS, FACTOR_RATES, FACTOR_OIL)


def test_factors_for_broad_skips_the_duplicate_spy():
    assert factors.factors_for(Sector.BROAD) == (FACTOR_SPY, FACTOR_RATES, FACTOR_OIL)


def test_factors_for_every_sector_is_a_subset_of_factor_names():
    for sector in Sector:
        names = factors.factors_for(sector)
        assert names[0] == FACTOR_SPY
        assert list(names) == [n for n in FACTOR_NAMES if n in names]


# ------------------------------------------------------------------ estimator


def test_ridge_recovers_synthetic_betas():
    f = make_factors()
    true = {FACTOR_SPY: 1.1, "XLK": 0.6, FACTOR_RATES: -0.3, FACTOR_OIL: 0.15}
    stocks = pd.DataFrame({"AAA": make_stock(f, true, intercept=0.0004)})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"AAA": Sector.TECHNOLOGY}, alpha=OLS)["AAA"]

    assert fit.ticker == "AAA" and fit.sector == Sector.TECHNOLOGY
    assert set(fit.betas) == set(factors.factors_for(Sector.TECHNOLOGY))
    for name, beta in true.items():
        assert fit.betas[name] == pytest.approx(beta, abs=0.05), name
    assert fit.intercept == pytest.approx(0.0004, abs=2e-4)
    assert 0.9 < fit.r2 <= 1.0
    assert fit.flags == ()


def test_betas_are_in_raw_units_for_differently_scaled_factors():
    f = make_factors()
    f[FACTOR_RATES] *= 10  # a factor ten times wider must still give its raw beta
    true = {FACTOR_SPY: 0.8, FACTOR_RATES: -0.05, FACTOR_OIL: 0.4}
    stocks = pd.DataFrame({"BRD": make_stock(f, true)})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"]

    assert fit.betas[FACTOR_RATES] == pytest.approx(-0.05, abs=0.005)
    assert fit.betas[FACTOR_SPY] == pytest.approx(0.8, abs=0.05)


def test_ridge_penalty_scales_with_n_obs():
    """Independent standardized factors: b_std = OLS_std / (1 + alpha), so beta halves at alpha = 1."""
    f = make_factors()
    stocks = pd.DataFrame({"BRD": make_stock(f, {FACTOR_SPY: 1.2}, noise=0.001)})

    ols = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"]
    ridge = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=1.0)["BRD"]

    assert ols.betas[FACTOR_SPY] == pytest.approx(1.2, abs=0.02)
    assert ridge.betas[FACTOR_SPY] == pytest.approx(0.6, abs=0.05)


def test_intercept_is_not_penalized():
    f = make_factors()
    window = in_window(f.index)
    f.loc[window, FACTOR_SPY] -= f.loc[window, FACTOR_SPY].mean()  # so the intercept is mean(y) exactly
    stocks = pd.DataFrame({"BRD": make_stock(f, {FACTOR_SPY: 1.0}, intercept=0.002, noise=0.001)})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=100.0)["BRD"]

    assert abs(fit.betas[FACTOR_SPY]) < 0.05
    assert fit.intercept == pytest.approx(0.002, abs=3e-4)


def test_one_fit_per_stock_column():
    f = make_factors()
    stocks = pd.DataFrame({
        "TECH": make_stock(f, {FACTOR_SPY: 1.0, "XLK": 0.5}, seed=2),
        "OIL": make_stock(f, {FACTOR_SPY: 0.7, "XLE": 0.9}, seed=3),
    })

    fits = factors.fit_betas(
        stocks, f, AS_OF, sectors={"TECH": Sector.TECHNOLOGY, "OIL": Sector.ENERGY}, alpha=OLS
    )

    assert set(fits) == {"TECH", "OIL"}
    assert fits["TECH"].betas["XLK"] == pytest.approx(0.5, abs=0.05)
    assert fits["OIL"].betas["XLE"] == pytest.approx(0.9, abs=0.05)
    assert "XLE" not in fits["TECH"].betas


def test_semiconductors_get_the_soxx_factor():
    f = make_factors()
    true = {FACTOR_SPY: 1.0, "XLK": 0.4, FACTOR_SEMIS: 0.9}
    stocks = pd.DataFrame({"CHIP": make_stock(f, true)})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"CHIP": Sector.SEMICONDUCTORS}, alpha=OLS)["CHIP"]

    assert fit.betas[FACTOR_SEMIS] == pytest.approx(0.9, abs=0.05)


# ------------------------------------------------------------------ rows used


def test_window_ends_before_as_of():
    f = make_factors()
    stocks = pd.DataFrame({"BRD": make_stock(f, {FACTOR_SPY: 1.0})})
    outside = ~in_window(f.index)
    stocks.loc[outside, "BRD"] = -5.0 * f.loc[outside, FACTOR_SPY] + 0.05  # poison every row outside

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"]

    assert fit.n_obs == int(in_window(f.index).sum())
    assert fit.betas[FACTOR_SPY] == pytest.approx(1.0, abs=0.05)


def test_as_of_row_is_excluded_and_window_start_row_is_included():
    f = make_factors()
    stocks = pd.DataFrame({"BRD": make_stock(f, {FACTOR_SPY: 1.0})})
    base = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"]

    on_as_of = stocks.copy()
    on_as_of.loc[pd.Timestamp(AS_OF), "BRD"] = 10.0
    assert factors.fit_betas(on_as_of, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"] == base

    start_dropped = stocks.copy()
    start_dropped.loc[pd.Timestamp(WINDOW_START), "BRD"] = np.nan
    fit = factors.fit_betas(start_dropped, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"]
    assert fit.n_obs == base.n_obs - 1


def test_window_years_argument():
    f = make_factors()
    stocks = pd.DataFrame({"BRD": make_stock(f, {FACTOR_SPY: 1.0})})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS, window_years=1)["BRD"]

    one_year = (f.index >= pd.Timestamp(date(2019, 6, 15))) & (f.index < pd.Timestamp(AS_OF))
    assert fit.n_obs == int(one_year.sum())


def test_nan_rows_dropped_only_for_the_stocks_own_factors():
    f = make_factors()
    stocks = pd.DataFrame({"TECH": make_stock(f, {FACTOR_SPY: 1.0, "XLK": 0.5})})
    base = factors.fit_betas(stocks, f, AS_OF, sectors={"TECH": Sector.TECHNOLOGY}, alpha=OLS)["TECH"]

    window_days = f.index[in_window(f.index)]
    f_gaps = f.copy()
    f_gaps.loc[window_days[:50], "XLE"] = np.nan  # not a technology factor
    f_gaps.loc[window_days[100:110], "XLK"] = np.nan  # a technology factor
    stocks_gaps = stocks.copy()
    stocks_gaps.loc[window_days[200:205], "TECH"] = np.nan

    fit = factors.fit_betas(stocks_gaps, f_gaps, AS_OF, sectors={"TECH": Sector.TECHNOLOGY}, alpha=OLS)["TECH"]

    assert fit.n_obs == base.n_obs - 15
    assert fit.betas["XLK"] == pytest.approx(0.5, abs=0.05)


def test_stress_betas_use_only_stress_days():
    f = make_factors()
    stress = f[FACTOR_SPY] < factors.STRESS_SPY_RETURN
    y = np.where(stress, 2.0, 0.5) * f[FACTOR_SPY]
    stocks = pd.DataFrame({"BRD": y + np.random.default_rng(4).normal(0, 0.001, len(f))}, index=f.index)

    calm = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS)["BRD"]
    stressed = factors.fit_betas(
        stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS, stress_only=True
    )["BRD"]

    assert stressed.n_obs == int((stress & in_window(f.index)).sum())
    assert stressed.betas[FACTOR_SPY] == pytest.approx(2.0, abs=0.05)
    assert calm.betas[FACTOR_SPY] < 1.9


def test_stress_threshold_is_strict():
    f = make_factors()
    window_days = f.index[in_window(f.index)]
    f.loc[window_days[:30], FACTOR_SPY] = factors.STRESS_SPY_RETURN  # exactly -1%: not a stress day
    stocks = pd.DataFrame({"BRD": make_stock(f, {FACTOR_SPY: 1.0})})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"BRD": Sector.BROAD}, alpha=OLS, stress_only=True)["BRD"]

    expected = (f[FACTOR_SPY] < factors.STRESS_SPY_RETURN) & in_window(f.index)
    assert fit.n_obs == int(expected.sum())


# ------------------------------------------------------------------ flags and omissions


def test_unknown_sector_falls_back_to_spy():
    f = make_factors()
    stocks = pd.DataFrame({"ZZZ": make_stock(f, {FACTOR_SPY: 0.9, FACTOR_OIL: 0.2})})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={}, alpha=OLS)["ZZZ"]

    assert fit.sector == Sector.BROAD
    assert "sector_unknown" in fit.flags
    assert set(fit.betas) == set(factors.factors_for(Sector.BROAD))
    assert fit.betas[FACTOR_SPY] == pytest.approx(0.9, abs=0.05)


def test_known_sector_is_not_flagged_unknown():
    f = make_factors()
    stocks = pd.DataFrame({"AAA": make_stock(f, {FACTOR_SPY: 1.0})})

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"AAA": Sector.BROAD}, alpha=OLS)["AAA"]

    assert "sector_unknown" not in fit.flags


def test_short_history_flagged():
    f = make_factors()
    stocks = pd.DataFrame({"NEW": make_stock(f, {FACTOR_SPY: 1.0})})
    window_days = f.index[in_window(f.index)]
    stocks.loc[window_days[:-100], "NEW"] = np.nan  # listed 100 days before as_of

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"NEW": Sector.BROAD}, alpha=OLS)["NEW"]

    assert fit.n_obs == 100 < factors.MIN_FACTOR_OBS
    assert "low_history" in fit.flags


def test_exactly_min_factor_obs_is_not_low_history():
    f = make_factors()
    stocks = pd.DataFrame({"NEW": make_stock(f, {FACTOR_SPY: 1.0})})
    window_days = f.index[in_window(f.index)]
    stocks.loc[window_days[: -factors.MIN_FACTOR_OBS], "NEW"] = np.nan

    fit = factors.fit_betas(stocks, f, AS_OF, sectors={"NEW": Sector.BROAD}, alpha=OLS)["NEW"]

    assert fit.n_obs == factors.MIN_FACTOR_OBS
    assert "low_history" not in fit.flags


def test_too_little_history_is_omitted():
    f = make_factors()
    stocks = pd.DataFrame({
        "OLD": make_stock(f, {FACTOR_SPY: 1.0}, seed=5),
        "IPO": make_stock(f, {FACTOR_SPY: 1.0}, seed=6),
    })
    window_days = f.index[in_window(f.index)]
    stocks.loc[window_days[: -(factors.MIN_FIT_OBS - 1)], "IPO"] = np.nan
    stocks.loc[f.index >= pd.Timestamp(AS_OF), "IPO"] = 0.0  # rows after as_of never count

    fits = factors.fit_betas(stocks, f, AS_OF, sectors={"OLD": Sector.BROAD, "IPO": Sector.BROAD}, alpha=OLS)

    assert set(fits) == {"OLD"}


# ------------------------------------------------------------------ estimate_return


def fit_with(betas: dict[str, float], intercept: float = 0.01) -> factors.BetaFit:
    return factors.BetaFit(ticker="T", sector=Sector.TECHNOLOGY, betas=betas, intercept=intercept, r2=0.5, n_obs=500)


def test_estimate_return_is_beta_times_moves_without_intercept():
    fit = fit_with({FACTOR_SPY: 1.2, "XLK": 0.5, FACTOR_RATES: -0.1, FACTOR_OIL: 0.05})
    moves = {FACTOR_SPY: -0.05, "XLK": -0.08, FACTOR_RATES: 0.3, FACTOR_OIL: 0.1, "XLE": 9.9}

    expected = 1.2 * -0.05 + 0.5 * -0.08 + -0.1 * 0.3 + 0.05 * 0.1
    assert factors.estimate_return(fit, moves) == pytest.approx(expected, abs=1e-12)


def test_estimate_return_missing_factor_raises():
    fit = fit_with({FACTOR_SPY: 1.0, FACTOR_SEMIS: 0.8})
    with pytest.raises(KeyError):
        factors.estimate_return(fit, {FACTOR_SPY: -0.02})
