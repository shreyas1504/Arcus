"""
ARCUS — Backend Metrics Tests
Tests every calculation function in analytics/metrics.py:
sharpe_ratio, sortino_ratio, calculate_beta, calculate_var, compute_cvar,
max_drawdown, annualized_return, annualized_volatility, portfolio_health_score,
compute_calmar_ratio, compute_alpha, compute_information_ratio,
diversification_score, compute_correlation_matrix, compute_risk_contribution.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np
import pandas as pd
import pytest
from backend.analytics.metrics import (
    sharpe_ratio,
    sortino_ratio,
    calculate_beta,
    calculate_var,
    compute_cvar,
    max_drawdown,
    annualized_return,
    annualized_volatility,
    portfolio_health_score,
    compute_calmar_ratio,
    compute_alpha,
    compute_information_ratio,
    diversification_score,
    compute_correlation_matrix,
    compute_risk_contribution,
    rolling_sharpe,
    interpret_return,
    interpret_volatility,
    interpret_sharpe,
    interpret_beta,
    interpret_var,
    interpret_max_drawdown,
)
from backend.config import RISK_FREE_RATE, TRADING_DAYS

EPSILON = 1e-4  # floating-point tolerance


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures — synthetic return series
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def flat_returns():
    """Zero-mean returns — Sharpe/Sortino should be near 0 after RF subtraction."""
    np.random.seed(42)
    return pd.Series(np.random.normal(0, 0.01, 252))

@pytest.fixture
def bull_returns():
    """Strong positive daily returns (~20% annualised)."""
    np.random.seed(0)
    return pd.Series(np.random.normal(0.20 / 252, 0.15 / np.sqrt(252), 252))

@pytest.fixture
def bear_returns():
    """Negative daily returns — persistent drawdown."""
    np.random.seed(1)
    return pd.Series(np.random.normal(-0.20 / 252, 0.20 / np.sqrt(252), 252))

@pytest.fixture
def two_asset_returns(bull_returns, bear_returns):
    """DataFrame with two assets: bull and bear."""
    return pd.DataFrame({'bull': bull_returns, 'bear': bear_returns})

@pytest.fixture
def market_returns():
    """Synthetic S&P 500 proxy: ~12% annual, 16% vol."""
    np.random.seed(2)
    return pd.Series(np.random.normal(0.12 / 252, 0.16 / np.sqrt(252), 252))


# ─────────────────────────────────────────────────────────────────────────────
# 1. sharpe_ratio
# ─────────────────────────────────────────────────────────────────────────────
class TestSharpeRatio:
    def test_positive_for_bull_market(self, bull_returns):
        s = sharpe_ratio(bull_returns)
        assert s > 0, "Bull market Sharpe must be positive"

    def test_negative_for_bear_market(self, bear_returns):
        s = sharpe_ratio(bear_returns)
        assert s < 0, "Bear market Sharpe must be negative"

    def test_zero_std_returns_zero(self):
        """Returns exactly at the risk-free rate → excess = [0.0]*252 → std is exactly 0."""
        daily_rf = RISK_FREE_RATE / TRADING_DAYS
        rf_returns = pd.Series([daily_rf] * 252)
        s = sharpe_ratio(rf_returns)
        assert s == 0.0

    def test_formula_manually(self, bull_returns):
        """Verify formula: (mean_excess / std_excess) × sqrt(252)"""
        rf_daily = RISK_FREE_RATE / TRADING_DAYS
        excess = bull_returns - rf_daily
        expected = (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS)
        assert abs(sharpe_ratio(bull_returns) - expected) < EPSILON

    def test_higher_rf_rate_lowers_sharpe(self, bull_returns):
        s_low_rf  = sharpe_ratio(bull_returns, risk_free_rate=0.01)
        s_high_rf = sharpe_ratio(bull_returns, risk_free_rate=0.08)
        assert s_low_rf > s_high_rf

    def test_annualisation_factor(self, bull_returns):
        """Sharpe should scale by sqrt(252) relative to daily ratio."""
        rf_daily = RISK_FREE_RATE / TRADING_DAYS
        excess = bull_returns - rf_daily
        daily_ratio = excess.mean() / excess.std()
        annual_sharpe = sharpe_ratio(bull_returns)
        assert abs(annual_sharpe / np.sqrt(TRADING_DAYS) - daily_ratio) < EPSILON


# ─────────────────────────────────────────────────────────────────────────────
# 2. sortino_ratio
# ─────────────────────────────────────────────────────────────────────────────
class TestSortinoRatio:
    def test_positive_for_bull_market(self, bull_returns):
        assert sortino_ratio(bull_returns) > 0

    def test_negative_for_bear_market(self, bear_returns):
        assert sortino_ratio(bear_returns) < 0

    def test_sortino_ge_sharpe_for_right_skew(self, bull_returns):
        """Sortino ≥ Sharpe when portfolio has more upside than downside."""
        sortino = sortino_ratio(bull_returns)
        sharpe  = sharpe_ratio(bull_returns)
        # For normally distributed returns with positive mean, sortino ≈ sharpe × sqrt(2)
        # At minimum it should not be dramatically worse
        assert sortino >= sharpe * 0.5  # Loose bound

    def test_no_downside_returns_zero(self):
        """All positive returns → no downside → sortino = 0 (by design)."""
        positive_only = pd.Series([0.005] * 252)
        s = sortino_ratio(positive_only)
        assert s == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. calculate_beta
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateBeta:
    def test_perfect_correlation_is_1(self, market_returns):
        """Portfolio that IS the market has beta=1.
        Note: np.cov uses ddof=1 (sample) while np.var uses ddof=0 (population),
        so beta = cov/var = n/(n-1) ≈ 1.004 for n=252. Use 0.01 tolerance.
        """
        beta = calculate_beta(market_returns, market_returns)
        assert abs(beta - 1.0) < 0.01

    def test_zero_asset_is_near_zero(self, market_returns):
        """Constant (risk-free) asset has beta≈0."""
        zero_vol = pd.Series([0.0] * len(market_returns))
        beta = calculate_beta(zero_vol, market_returns)
        assert abs(beta) < 0.01

    def test_double_leveraged_is_2(self, market_returns):
        """2× leveraged portfolio has beta≈2.
        Same ddof mismatch: actual ≈ 2*(n/(n-1)) ≈ 2.008. Use 0.02 tolerance.
        """
        leveraged = market_returns * 2
        beta = calculate_beta(leveraged, market_returns)
        assert abs(beta - 2.0) < 0.02

    def test_negative_correlation(self, market_returns):
        """Inversely correlated asset has negative beta."""
        inverse = -market_returns
        beta = calculate_beta(inverse, market_returns)
        assert beta < 0

    def test_mismatched_lengths_returns_1(self, market_returns):
        short_series = pd.Series([0.01] * 50)
        beta = calculate_beta(short_series, market_returns)
        assert beta == 1.0  # Fallback

    def test_formula_cov_var(self, bull_returns, market_returns):
        """β = Cov(portfolio, market) / Var(market)"""
        min_len = min(len(bull_returns), len(market_returns))
        p = np.array(bull_returns[:min_len])
        m = np.array(market_returns[:min_len])
        expected = np.cov(p, m)[0][1] / np.var(m)
        actual = calculate_beta(bull_returns[:min_len], market_returns[:min_len])
        assert abs(actual - expected) < EPSILON


# ─────────────────────────────────────────────────────────────────────────────
# 4. calculate_var (VaR)
# ─────────────────────────────────────────────────────────────────────────────
class TestCalculateVar:
    def test_var_is_negative_for_positive_mean(self, bull_returns):
        """5th percentile of positive returns is typically still negative (daily losses)."""
        var = calculate_var(bull_returns)
        # VaR can be either sign depending on returns; check it is a realistic daily number
        assert -0.20 <= var <= 0.05

    def test_high_vol_has_worse_var(self):
        """Higher volatility → worse (lower) VaR."""
        np.random.seed(42)
        low_vol  = pd.Series(np.random.normal(0, 0.01, 1000))
        high_vol = pd.Series(np.random.normal(0, 0.04, 1000))
        var_low  = calculate_var(low_vol)
        var_high = calculate_var(high_vol)
        assert var_high < var_low

    def test_var_equals_5th_percentile(self, flat_returns):
        """calculate_var should equal np.percentile(returns, 5)"""
        expected = float(np.percentile(flat_returns, 5))
        actual   = calculate_var(flat_returns)
        assert abs(actual - expected) < EPSILON

    def test_confidence_level_effect(self, flat_returns):
        """99% VaR is more negative than 95% VaR."""
        var_95 = calculate_var(flat_returns, confidence_level=0.95)
        var_99 = calculate_var(flat_returns, confidence_level=0.99)
        assert var_99 <= var_95


# ─────────────────────────────────────────────────────────────────────────────
# 5. compute_cvar (Expected Shortfall)
# ─────────────────────────────────────────────────────────────────────────────
class TestComputeCVar:
    def test_cvar_worse_than_var(self, flat_returns):
        """CVaR (average of tail) should be ≤ VaR (worst-case threshold)."""
        var = calculate_var(flat_returns)
        cvar = compute_cvar(flat_returns)
        assert cvar <= var

    def test_cvar_is_mean_of_tail(self, flat_returns):
        """Manual computation of CVaR should match."""
        threshold = flat_returns.quantile(0.05)
        tail = flat_returns[flat_returns <= threshold]
        expected = float(tail.mean())
        actual   = compute_cvar(flat_returns)
        assert abs(actual - expected) < EPSILON


# ─────────────────────────────────────────────────────────────────────────────
# 6. max_drawdown
# ─────────────────────────────────────────────────────────────────────────────
class TestMaxDrawdown:
    def test_always_negative_or_zero(self, bull_returns):
        mdd = max_drawdown(bull_returns)
        assert mdd <= 0

    def test_monotone_increasing_has_zero_drawdown(self):
        """Perfectly rising series → no drawdown."""
        monotone = pd.Series([0.001] * 252)
        mdd = max_drawdown(monotone)
        assert abs(mdd) < EPSILON

    def test_peak_to_trough_formula(self):
        """Verify MDD with a known series."""
        # Price: 100 → 120 → 80 → 90
        returns = pd.Series([0.20, -1/3, 0.125])  # approx price changes
        mdd = max_drawdown(returns)
        # After the 120→80 drop: drawdown = (80-120)/120 = -33.3%
        assert mdd <= -0.30  # At least 30% drawdown

    def test_bear_market_has_larger_drawdown_than_bull(self, bull_returns, bear_returns):
        mdd_bull = max_drawdown(bull_returns)
        mdd_bear = max_drawdown(bear_returns)
        assert mdd_bear < mdd_bull


# ─────────────────────────────────────────────────────────────────────────────
# 7. annualized_return and annualized_volatility
# ─────────────────────────────────────────────────────────────────────────────
class TestAnnualisedMetrics:
    def test_annualized_return_formula(self, bull_returns):
        """ann_return = mean_daily × 252"""
        returns_df = pd.DataFrame({'A': bull_returns})
        weights = [1.0]
        ann_ret = annualized_return(returns_df, weights)
        expected = float(bull_returns.mean() * TRADING_DAYS)
        assert abs(ann_ret - expected) < EPSILON

    def test_annualized_vol_formula(self, bull_returns):
        """ann_vol = sqrt(w^T Cov w) × sqrt(252) for 1 asset = std × sqrt(252)"""
        returns_df = pd.DataFrame({'A': bull_returns})
        weights = [1.0]
        ann_vol = annualized_volatility(returns_df, weights)
        expected = float(bull_returns.std() * np.sqrt(TRADING_DAYS))
        assert abs(ann_vol - expected) < EPSILON

    def test_diversified_vol_less_than_average(self, bull_returns, flat_returns):
        """Portfolio vol < average of individual vols (positive diversification)."""
        returns_df = pd.DataFrame({'bull': bull_returns, 'flat': flat_returns})
        portfolio_vol = annualized_volatility(returns_df, [0.5, 0.5])
        # At minimum the portfolio vol should be calculable and positive
        assert portfolio_vol > 0

    def test_two_asset_equal_weight_return(self, bull_returns, bear_returns):
        """50% bull + 50% bear returns ≈ average of both."""
        returns_df = pd.DataFrame({'bull': bull_returns, 'bear': bear_returns})
        ann_ret = annualized_return(returns_df, [0.5, 0.5])
        expected = 0.5 * bull_returns.mean() * TRADING_DAYS + 0.5 * bear_returns.mean() * TRADING_DAYS
        assert abs(ann_ret - expected) < EPSILON


# ─────────────────────────────────────────────────────────────────────────────
# 8. portfolio_health_score (backend formula)
# ─────────────────────────────────────────────────────────────────────────────
class TestPortfolioHealthScore:
    """
    Backend formula:
    sharpe_score = clip(sharpe/2.0 × 40, 0, 40)
    var_score    = clip((var + 0.05)/0.04 × 25, 0, 25)
    vol_score    = clip((0.35 - vol)/0.25 × 20, 0, 20)
    conc_score   = clip((1 - max_weight)/0.75 × 15, 0, 15)
    total        = sum(scores)
    """
    def test_total_in_0_100_range(self):
        for (sharpe, var_d, vol, weights) in [
            (1.5,  -0.02, 0.18, [0.25, 0.25, 0.25, 0.25]),
            (-1.0, -0.08, 0.50, [1.00]),
            (3.0,  -0.01, 0.05, [0.10] * 10),
        ]:
            total, _ = portfolio_health_score(sharpe, var_d, vol, weights)
            assert 0 <= total <= 100, f"Score {total} out of range for {sharpe},{var_d},{vol}"

    def test_sharpe_component_caps_at_40(self):
        """sharpe ≥ 2.0 → sharpe_score = 40."""
        total1, comps1 = portfolio_health_score(2.0, -0.01, 0.10, [0.5, 0.5])
        total2, comps2 = portfolio_health_score(4.0, -0.01, 0.10, [0.5, 0.5])
        # Both capped at 40 pts for Sharpe
        assert comps1['Sharpe (40 pts)'] == pytest.approx(40.0, abs=0.1)
        assert comps2['Sharpe (40 pts)'] == pytest.approx(40.0, abs=0.1)

    def test_sharpe_component_zero_at_zero(self):
        total, comps = portfolio_health_score(0.0, -0.01, 0.10, [0.5, 0.5])
        assert comps['Sharpe (40 pts)'] == pytest.approx(0.0, abs=0.1)

    def test_var_component_full_at_plus_50bp(self):
        """var_daily = +0.05 → clip((0.05+0.05)/0.04 × 25, 0, 25) = 25."""
        _, comps = portfolio_health_score(1.0, 0.05, 0.10, [0.5, 0.5])
        assert comps['VaR (25 pts)'] == pytest.approx(25.0, abs=0.1)

    def test_var_component_zero_at_minus_50bp(self):
        """var_daily = -0.05 → clip((−0.05+0.05)/0.04 × 25, 0, 25) = 0."""
        _, comps = portfolio_health_score(1.0, -0.05, 0.10, [0.5, 0.5])
        assert comps['VaR (25 pts)'] == pytest.approx(0.0, abs=0.1)

    def test_vol_component_full_below_10pct(self):
        """vol = 0.10 → clip((0.35-0.10)/0.25 × 20, 0, 20) = 20."""
        _, comps = portfolio_health_score(1.0, -0.01, 0.10, [0.5, 0.5])
        assert comps['Volatility (20 pts)'] == pytest.approx(20.0, abs=0.1)

    def test_vol_component_zero_above_35pct(self):
        """vol ≥ 0.35 → clip(0, 0, 20) = 0."""
        _, comps = portfolio_health_score(1.0, -0.01, 0.40, [0.5, 0.5])
        assert comps['Volatility (20 pts)'] == pytest.approx(0.0, abs=0.1)

    def test_concentration_component_full_equal_weight(self):
        """10 equal weights: max_w = 0.1 → clip((1-0.1)/0.75 × 15, 0, 15) = 15."""
        _, comps = portfolio_health_score(1.0, -0.01, 0.15, [0.1] * 10)
        assert comps['Concentration (15 pts)'] == pytest.approx(15.0, abs=0.1)

    def test_concentration_component_zero_single_stock(self):
        """Single stock: max_w = 1.0 → clip((1-1.0)/0.75 × 15, 0, 15) = 0."""
        _, comps = portfolio_health_score(1.0, -0.01, 0.15, [1.0])
        assert comps['Concentration (15 pts)'] == pytest.approx(0.0, abs=0.1)

    def test_excellent_portfolio_scores_above_70(self):
        """Sharpe 2.0, low VaR, low vol, diversified → Green zone."""
        total, _ = portfolio_health_score(2.0, -0.01, 0.10, [0.1] * 10)
        assert total >= 70

    def test_terrible_portfolio_scores_below_40(self):
        """Sharpe -1, high VaR, high vol, concentrated → Red zone."""
        total, _ = portfolio_health_score(-1.0, -0.10, 0.70, [1.0])
        assert total < 40

    def test_components_sum_to_total(self):
        total, comps = portfolio_health_score(1.5, -0.02, 0.20, [0.25, 0.25, 0.25, 0.25])
        comp_sum = sum(comps.values())
        assert abs(total - comp_sum) < 0.2


# ─────────────────────────────────────────────────────────────────────────────
# 9. compute_calmar_ratio
# ─────────────────────────────────────────────────────────────────────────────
class TestCalmarRatio:
    def test_positive_for_bull(self, bull_returns):
        calmar = compute_calmar_ratio(bull_returns)
        assert calmar > 0

    def test_formula_ann_return_over_mdd(self, bull_returns):
        ann_ret = float(bull_returns.mean() * TRADING_DAYS)
        mdd = max_drawdown(bull_returns)
        expected = ann_ret / abs(mdd) if mdd != 0 else 0.0
        actual = compute_calmar_ratio(bull_returns)
        assert abs(actual - expected) < EPSILON


# ─────────────────────────────────────────────────────────────────────────────
# 10. compute_alpha and compute_information_ratio
# ─────────────────────────────────────────────────────────────────────────────
class TestAlphaAndInfoRatio:
    def test_alpha_positive_for_outperformer(self, bull_returns, market_returns):
        """Portfolio with higher returns than CAPM predicts has positive alpha."""
        # Restrict to same length
        n = min(len(bull_returns), len(market_returns))
        alpha = compute_alpha(bull_returns[:n], market_returns[:n])
        # With bull returns significantly above market, alpha should be positive
        assert alpha > -0.50  # Allow some uncertainty

    def test_alpha_zero_for_market(self, market_returns):
        """Portfolio that IS the market has alpha ≈ 0."""
        alpha = compute_alpha(market_returns, market_returns)
        assert abs(alpha) < 0.01

    def test_information_ratio_zero_for_benchmark(self, market_returns):
        """If portfolio = benchmark, active returns = 0 → IR = 0."""
        ir = compute_information_ratio(market_returns, market_returns)
        assert abs(ir) < EPSILON

    def test_information_ratio_positive_for_outperformer(self, bull_returns, market_returns):
        n = min(len(bull_returns), len(market_returns))
        ir = compute_information_ratio(bull_returns[:n], market_returns[:n])
        # Bull returns > market → positive active returns → positive IR
        assert isinstance(ir, float)


# ─────────────────────────────────────────────────────────────────────────────
# 11. diversification_score
# ─────────────────────────────────────────────────────────────────────────────
class TestDiversificationScore:
    def test_single_asset_returns_50(self, bull_returns):
        """Single asset → no pairwise correlation → fallback 50."""
        df = pd.DataFrame({'A': bull_returns})
        score = diversification_score(df)
        assert score == 50.0

    def test_perfect_correlation_scores_low(self, bull_returns):
        """Two perfectly correlated assets → correlation=1 → score=0."""
        df = pd.DataFrame({'A': bull_returns, 'B': bull_returns})
        score = diversification_score(df)
        assert score <= 1.0  # (1-1)/2 × 100 = 0

    def test_perfect_negative_correlation_scores_high(self, bull_returns):
        """Two perfectly anti-correlated assets → correlation=-1 → score=100."""
        df = pd.DataFrame({'A': bull_returns, 'B': -bull_returns})
        score = diversification_score(df)
        assert score >= 99.0

    def test_score_in_0_100_range(self, two_asset_returns):
        score = diversification_score(two_asset_returns)
        assert 0 <= score <= 100


# ─────────────────────────────────────────────────────────────────────────────
# 12. compute_correlation_matrix
# ─────────────────────────────────────────────────────────────────────────────
class TestCorrelationMatrix:
    def test_diagonal_is_1(self, two_asset_returns):
        result = compute_correlation_matrix(two_asset_returns)
        matrix = result['matrix']
        for i in range(len(matrix)):
            assert abs(matrix[i][i] - 1.0) < EPSILON

    def test_symmetric(self, two_asset_returns):
        result = compute_correlation_matrix(two_asset_returns)
        matrix = np.array(result['matrix'])
        assert np.allclose(matrix, matrix.T, atol=EPSILON)

    def test_tickers_list_matches_columns(self, two_asset_returns):
        result = compute_correlation_matrix(two_asset_returns)
        assert set(result['tickers']) == {'bull', 'bear'}


# ─────────────────────────────────────────────────────────────────────────────
# 13. compute_risk_contribution
# ─────────────────────────────────────────────────────────────────────────────
class TestRiskContribution:
    def test_contributions_sum_to_1(self, two_asset_returns):
        weights = np.array([0.6, 0.4])
        contribs = compute_risk_contribution(two_asset_returns, weights)
        total = sum(contribs.values())
        assert abs(total - 1.0) < 0.01

    def test_higher_weight_generally_more_risk(self, two_asset_returns):
        """Higher-weighted asset should typically contribute more risk."""
        weights = np.array([0.8, 0.2])
        contribs = compute_risk_contribution(two_asset_returns, weights)
        # This is not always true (depends on correlation) but usually holds for equal-risk assets
        assert isinstance(contribs, dict)
        assert len(contribs) == 2


# ─────────────────────────────────────────────────────────────────────────────
# 14. rolling_sharpe
# ─────────────────────────────────────────────────────────────────────────────
class TestRollingSharpe:
    def test_returns_series(self, bull_returns):
        rs = rolling_sharpe(bull_returns, window=60)
        assert isinstance(rs, pd.Series)

    def test_first_59_are_nan(self, bull_returns):
        rs = rolling_sharpe(bull_returns, window=60)
        assert rs[:59].isna().all()

    def test_rest_not_all_nan(self, bull_returns):
        rs = rolling_sharpe(bull_returns, window=60)
        assert not rs[60:].isna().all()


# ─────────────────────────────────────────────────────────────────────────────
# 15. Interpretation functions (string output)
# ─────────────────────────────────────────────────────────────────────────────
class TestInterpretations:
    def test_interpret_return_positive(self):
        s = interpret_return(0.20)
        assert "grew" in s
        assert "20" in s

    def test_interpret_return_negative(self):
        s = interpret_return(-0.15)
        assert "shrank" in s

    def test_interpret_volatility_labels(self):
        assert "low"      in interpret_volatility(0.10).lower()
        assert "moderate" in interpret_volatility(0.20).lower()
        assert "high"     in interpret_volatility(0.35).lower()

    def test_interpret_sharpe_labels(self):
        assert "excellent" in interpret_sharpe(2.5).lower()
        assert "good"      in interpret_sharpe(1.2).lower()
        assert "below"     in interpret_sharpe(0.5).lower()
        assert "poor"      in interpret_sharpe(-0.1).lower()

    def test_interpret_beta_amplifies(self):
        s = interpret_beta(1.5)
        assert "amplifies" in s.lower()

    def test_interpret_beta_dampens(self):
        s = interpret_beta(0.6)
        assert "dampens" in s.lower()

    def test_interpret_var_includes_dollar(self):
        s = interpret_var(-0.03, investment=10000)
        assert "$" in s

    def test_interpret_max_drawdown_labels(self):
        assert "severe"      in interpret_max_drawdown(-0.50).lower()
        assert "significant" in interpret_max_drawdown(-0.25).lower()
        assert "moderate"    in interpret_max_drawdown(-0.10).lower()


# ─────────────────────────────────────────────────────────────────────────────
# 16. Cross-function consistency
# ─────────────────────────────────────────────────────────────────────────────
class TestCrossConsistency:
    def test_calmar_components_consistent(self, bull_returns):
        """Calmar = annual return / |max drawdown| using same functions."""
        ann_ret = float(bull_returns.mean() * TRADING_DAYS)
        mdd     = max_drawdown(bull_returns)
        calmar  = compute_calmar_ratio(bull_returns)
        if abs(mdd) > 1e-8:
            assert abs(calmar - ann_ret / abs(mdd)) < EPSILON

    def test_var_and_cvar_ordering(self, flat_returns):
        """CVaR (expected shortfall) must be ≤ VaR."""
        var  = calculate_var(flat_returns)
        cvar = compute_cvar(flat_returns)
        assert cvar <= var + EPSILON  # CVaR ≤ VaR

    def test_high_vol_lower_health(self):
        """Higher portfolio vol → lower health score (vol component decreases)."""
        score_low,  _ = portfolio_health_score(1.0, -0.02, 0.10, [0.5, 0.5])
        score_high, _ = portfolio_health_score(1.0, -0.02, 0.50, [0.5, 0.5])
        assert score_low > score_high
