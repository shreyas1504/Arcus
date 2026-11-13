"""Implementer tests for scenario/factors.py (Claude, C2).

Cursor's blind tests live in test_scenario_factors.py; these are separate on purpose.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from scenario.enums import FACTOR_NAMES, Sector
from scenario.factors import (
    MIN_FACTOR_OBS,
    MIN_FIT_OBS,
    BetaFit,
    estimate_return,
    factors_for,
    fit_betas,
)

AS_OF = date(2024, 6, 3)


def _factors(n: int = 900, seed: int = 0, end: str = "2024-05-31") -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.bdate_range(end=end, periods=n)
    data = rng.normal(0, 0.01, size=(n, len(FACTOR_NAMES)))
    return pd.DataFrame(data, index=index, columns=list(FACTOR_NAMES))


def _stock(factors: pd.DataFrame, betas: dict[str, float], noise: float = 0.002, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng(seed)
    y = sum(beta * factors[name] for name, beta in betas.items())
    return y + rng.normal(0, noise, size=len(factors)) + 0.0002


def test_factors_for_order_and_membership():
    assert factors_for(Sector.TECHNOLOGY) == ("SPY", "XLK", "DGS10_CHG", "BRENT")
    assert factors_for(Sector.SEMICONDUCTORS) == ("SPY", "XLK", "SOXX", "DGS10_CHG", "BRENT")
    assert factors_for(Sector.BROAD) == ("SPY", "DGS10_CHG", "BRENT")


def test_ols_limit_recovers_betas():
    f = _factors()
    true = {"SPY": 1.2, "XLE": 0.6, "DGS10_CHG": -0.3, "BRENT": 0.25}
    stocks = pd.DataFrame({"OILCO": _stock(f, true)})
    fit = fit_betas(stocks, f, AS_OF, sectors={"OILCO": Sector.ENERGY}, alpha=1e-9)["OILCO"]
    for name, beta in true.items():
        assert fit.betas[name] == pytest.approx(beta, abs=0.05)
    assert fit.intercept == pytest.approx(0.0002, abs=0.0005)
    assert fit.r2 > 0.9
    assert fit.flags == ()


def test_ridge_shrinks_toward_zero():
    f = _factors()
    stocks = pd.DataFrame({"A": _stock(f, {"SPY": 1.0, "XLK": 0.5})})
    small = fit_betas(stocks, f, AS_OF, sectors={"A": Sector.TECHNOLOGY}, alpha=1e-6)["A"]
    big = fit_betas(stocks, f, AS_OF, sectors={"A": Sector.TECHNOLOGY}, alpha=10.0)["A"]
    assert abs(big.betas["SPY"]) < abs(small.betas["SPY"]) / 5


def test_window_excludes_as_of_and_after():
    f = _factors(end="2024-12-31", n=1200)
    y = _stock(f, {"SPY": 1.0})
    # Poison everything on/after as_of: a leak would wreck the fit.
    y[y.index >= pd.Timestamp(AS_OF)] = 5.0
    fit = fit_betas(pd.DataFrame({"A": y}), f, AS_OF, sectors={"A": Sector.BROAD}, alpha=1e-9)["A"]
    assert fit.betas["SPY"] == pytest.approx(1.0, abs=0.05)
    expected = int(((f.index >= pd.Timestamp(AS_OF) - pd.DateOffset(years=3)) & (f.index < pd.Timestamp(AS_OF))).sum())
    assert fit.n_obs == expected


def test_window_years_limits_rows():
    f = _factors(n=900)
    stocks = pd.DataFrame({"A": _stock(f, {"SPY": 1.0})})
    one = fit_betas(stocks, f, AS_OF, sectors={"A": Sector.BROAD}, window_years=1)["A"]
    three = fit_betas(stocks, f, AS_OF, sectors={"A": Sector.BROAD}, window_years=3)["A"]
    assert 240 <= one.n_obs <= 270
    assert three.n_obs > 2.5 * one.n_obs


def test_stress_only_uses_only_stress_days():
    f = _factors()
    stocks = pd.DataFrame({"A": _stock(f, {"SPY": 1.0})})
    fit = fit_betas(stocks, f, AS_OF, sectors={"A": Sector.BROAD}, stress_only=True, alpha=1e-9)["A"]
    window = f[(f.index >= pd.Timestamp(AS_OF) - pd.DateOffset(years=3)) & (f.index < pd.Timestamp(AS_OF))]
    assert fit.n_obs == int((window["SPY"] < -0.01).sum())


def test_unknown_sector_falls_back_to_broad():
    f = _factors()
    fit = fit_betas(pd.DataFrame({"X": _stock(f, {"SPY": 1.0})}), f, AS_OF, sectors={})["X"]
    assert fit.sector is Sector.BROAD
    assert set(fit.betas) == {"SPY", "DGS10_CHG", "BRENT"}
    assert "sector_unknown" in fit.flags


def test_short_history_flagged_and_too_short_omitted():
    f = _factors()
    y = _stock(f, {"SPY": 1.0})
    short = y.copy()
    short[short.index < short.index[-(MIN_FACTOR_OBS - 10)]] = np.nan
    tiny = y.copy()
    tiny[tiny.index < tiny.index[-(MIN_FIT_OBS - 5)]] = np.nan
    fits = fit_betas(pd.DataFrame({"S": short, "T": tiny}), f, AS_OF, sectors={"S": Sector.BROAD, "T": Sector.BROAD})
    assert "low_history" in fits["S"].flags
    assert "T" not in fits


def test_semis_proxy_when_soxx_missing():
    f = _factors()
    f.loc[f.index < f.index[400], "SOXX"] = np.nan
    stocks = pd.DataFrame({"CHIP": _stock(f.fillna(0), {"SPY": 1.0, "XLK": 0.8})})
    fit = fit_betas(stocks, f, AS_OF, sectors={"CHIP": Sector.SEMICONDUCTORS}, window_years=3)["CHIP"]
    assert "semis_proxy" in fit.flags
    assert "SOXX" not in fit.betas
    assert fit.n_obs > 600  # rows kept, not dropped for SOXX


def test_semis_uses_soxx_when_available():
    f = _factors()
    true = {"SPY": 0.9, "XLK": 0.4, "SOXX": 0.7}
    fit = fit_betas(
        pd.DataFrame({"CHIP": _stock(f, true)}), f, AS_OF, sectors={"CHIP": Sector.SEMICONDUCTORS}, alpha=1e-9
    )["CHIP"]
    assert fit.betas["SOXX"] == pytest.approx(0.7, abs=0.05)
    assert "semis_proxy" not in fit.flags


def test_constant_factor_gets_zero_beta():
    f = _factors()
    f["BRENT"] = 0.0
    fit = fit_betas(pd.DataFrame({"A": _stock(f, {"SPY": 1.0})}), f, AS_OF, sectors={"A": Sector.BROAD}, alpha=1e-9)["A"]
    assert fit.betas["BRENT"] == 0.0
    assert fit.betas["SPY"] == pytest.approx(1.0, abs=0.05)


def test_timezone_aware_index_is_handled():
    f = _factors()
    y = _stock(f, {"SPY": 1.0})
    y.index = y.index.tz_localize("America/New_York")
    fit = fit_betas(pd.DataFrame({"A": y}), f, AS_OF, sectors={"A": Sector.BROAD}, alpha=1e-9)["A"]
    assert fit.betas["SPY"] == pytest.approx(1.0, abs=0.05)


def test_negative_alpha_rejected():
    f = _factors()
    with pytest.raises(ValueError):
        fit_betas(pd.DataFrame({"A": _stock(f, {"SPY": 1.0})}), f, AS_OF, sectors={}, alpha=-1)


def test_estimate_return():
    fit = BetaFit("A", Sector.BROAD, {"SPY": 1.5, "DGS10_CHG": -0.02, "BRENT": 0.1}, 0.001, 0.8, 500)
    moves = {"SPY": -0.10, "DGS10_CHG": -0.5, "BRENT": 0.2, "XLK": 9.0}
    assert estimate_return(fit, moves) == pytest.approx(-0.15 + 0.01 + 0.02)
    with pytest.raises(KeyError):
        estimate_return(fit, {"SPY": -0.1})
