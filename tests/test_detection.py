"""
Tests for fdd/detection.py.

Since fdd/features.py doesn't exist yet, we build PriceFeatures by hand
for each of the four regimes described in PROJECT_HANDOFF.md:
  1. Stable        -> flat price, tiny/cosmetic discount -> Genuine or Uncertain, low suspicion
  2. Genuine        -> long stable hold, real drop, stays low -> Genuine
  3. Gradual drift   -> slow trend, not manipulation -> not Suspicious
  4. Dark pattern    -> spike right before "sale" -> Suspicious

These fakes are hand-built now; once fdd/features.py exists and produces
real PriceFeatures from fdd/generator.py's synthetic series, swap these
fixtures for the real pipeline output (see test_integration.py, later).
"""

import pytest

from fdd.schema import PriceFeatures
from fdd.detection import (
    analyze,
    compute_suspicion,
    compute_volatility_score,
    compute_confidence,
    assign_status,
)


def make_features(**overrides) -> PriceFeatures:
    """Sane defaults, override per-test for the regime under test."""
    defaults = dict(
        product_id="TEST-001",
        n_days_history=90,
        claimed_original_price=100.0,
        claimed_sale_price=80.0,
        sale_date=None,
        days_original_price_held=60,
        pre_sale_spike_pct=0.0,
        sale_price_percentile=0.30,
        pct_below_median=0.20,
        coefficient_of_variation=0.05,
        volatility_label="low",
        trend_slope_per_day=0.0,
    )
    defaults.update(overrides)
    return PriceFeatures(**defaults)


# ---------------------------------------------------------------------------
# Regime 1: Stable — flat price, cosmetic discount
# ---------------------------------------------------------------------------

def test_stable_regime_low_suspicion():
    f = make_features(
        days_original_price_held=85,
        pre_sale_spike_pct=0.0,
        sale_price_percentile=0.55,   # barely below typical
        pct_below_median=0.03,        # cosmetic discount
        coefficient_of_variation=0.02,
    )
    result = analyze(f)
    assert result.suspicion_score < 0.55
    assert result.status in ("Genuine", "Uncertain")


# ---------------------------------------------------------------------------
# Regime 2: Genuine discount — long hold, real sustained drop
# ---------------------------------------------------------------------------

def test_genuine_discount_regime():
    f = make_features(
        n_days_history=120,
        days_original_price_held=90,
        pre_sale_spike_pct=0.0,
        sale_price_percentile=0.10,   # genuinely low
        pct_below_median=0.35,
        coefficient_of_variation=0.06,
    )
    result = analyze(f)
    assert result.status == "Genuine"
    assert result.suspicion_score < 0.4
    assert result.confidence > 0.5


# ---------------------------------------------------------------------------
# Regime 3: Gradual drift — slow trend, not manipulation
# ---------------------------------------------------------------------------

def test_gradual_drift_not_suspicious():
    f = make_features(
        n_days_history=100,
        days_original_price_held=40,
        pre_sale_spike_pct=0.05,      # small, not a real spike
        sale_price_percentile=0.45,
        pct_below_median=0.10,
        coefficient_of_variation=0.08,
        trend_slope_per_day=-0.15,    # slow downward drift
    )
    result = analyze(f)
    assert result.status != "Suspicious"


# ---------------------------------------------------------------------------
# Regime 4: Dark pattern — spike right before the sale
# ---------------------------------------------------------------------------

def test_dark_pattern_regime_flagged_suspicious():
    f = make_features(
        n_days_history=90,
        days_original_price_held=4,     # "original" barely held at all
        pre_sale_spike_pct=0.40,        # sharp spike right before sale
        sale_price_percentile=0.85,     # "sale" price still near the top of history
        pct_below_median=0.02,
        coefficient_of_variation=0.18,
        trend_slope_per_day=0.3,
    )
    result = analyze(f)
    assert result.status == "Suspicious"
    assert result.suspicion_score >= 0.55
    factor_names = {factor.name for factor in result.factors}
    assert "pre_sale_spike" in factor_names
    assert "short_original_price_hold" in factor_names


# ---------------------------------------------------------------------------
# Confidence / short-history gating
# ---------------------------------------------------------------------------

def test_short_history_forces_uncertain():
    f = make_features(
        n_days_history=5,               # far too short to trust
        pre_sale_spike_pct=0.40,        # even with strong spike signal...
        days_original_price_held=1,
        sale_price_percentile=0.90,
    )
    result = analyze(f)
    assert result.confidence < 0.5
    assert result.status == "Uncertain"


def test_confidence_increases_with_history_length():
    short = compute_confidence(make_features(n_days_history=10))
    medium = compute_confidence(make_features(n_days_history=30))
    long_ = compute_confidence(make_features(n_days_history=90))
    assert short < medium < long_


# ---------------------------------------------------------------------------
# Volatility score — independent of suspicion
# ---------------------------------------------------------------------------

def test_volatility_score_scales_with_cv():
    low = compute_volatility_score(make_features(coefficient_of_variation=0.01))
    mid = compute_volatility_score(make_features(coefficient_of_variation=0.15))
    high = compute_volatility_score(make_features(coefficient_of_variation=0.50))
    assert low < mid < high
    assert 0.0 <= low <= 1.0
    assert 0.0 <= high <= 1.0


def test_volatility_independent_of_suspicion():
    # high volatility but no suspicious signals -> suspicion should stay low
    f = make_features(
        coefficient_of_variation=0.40,   # high volatility
        pre_sale_spike_pct=0.0,
        days_original_price_held=80,
        sale_price_percentile=0.15,
        pct_below_median=0.30,
    )
    result = analyze(f)
    assert result.volatility_score > 0.5
    assert result.suspicion_score < 0.55


# ---------------------------------------------------------------------------
# assign_status boundary behavior
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "suspicion,confidence,expected",
    [
        (0.80, 0.90, "Suspicious"),
        (0.10, 0.90, "Genuine"),
        (0.40, 0.90, "Uncertain"),   # ambiguous zone
        (0.90, 0.30, "Uncertain"),   # low confidence overrides high suspicion
        (0.10, 0.30, "Uncertain"),   # low confidence overrides low suspicion too
    ],
)
def test_assign_status_boundaries(suspicion, confidence, expected):
    assert assign_status(suspicion, confidence) == expected


# ---------------------------------------------------------------------------
# Isolation Forest cross-check — informational only, doesn't move status
# ---------------------------------------------------------------------------

def test_isolation_forest_crosscheck_is_informational_only():
    target = make_features(
        pre_sale_spike_pct=0.40,
        days_original_price_held=4,
        sale_price_percentile=0.85,
    )
    reference_population = [
        make_features(product_id=f"REF-{i}", pre_sale_spike_pct=0.0, days_original_price_held=70)
        for i in range(15)
    ]

    result_with_ref = analyze(target, reference_population=reference_population)
    result_without_ref = analyze(target)

    # status/suspicion_score must be identical whether or not the cross-check ran
    assert result_with_ref.status == result_without_ref.status
    assert result_with_ref.suspicion_score == result_without_ref.suspicion_score

    factor_names = {f.name for f in result_with_ref.factors}
    # cross-check factor is present only when sklearn is installed and ref pop is big enough
    if "isolation_forest_cross_check" in factor_names:
        cross_check_factor = next(
            f for f in result_with_ref.factors if f.name == "isolation_forest_cross_check"
        )
        assert cross_check_factor.contribution == 0.0


def test_isolation_forest_skipped_with_small_reference_population():
    target = make_features()
    small_ref = [make_features(product_id=f"REF-{i}") for i in range(3)]
    result = analyze(target, reference_population=small_ref)
    factor_names = {f.name for f in result.factors}
    assert "isolation_forest_cross_check" not in factor_names
