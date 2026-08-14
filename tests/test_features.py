"""
tests/test_features.py

Unit tests for fdd/features.py.
Uses the synthetic generator to get realistic DataFrames, so we can verify
that features look meaningfully different across the four regimes.
"""

import pytest
import pandas as pd
import numpy as np

from fdd.generator import generate_series, Regime
from fdd.features import extract_features


def get_features(regime: Regime, seed: int = 1, base_price: float = 1000.0):
    s = generate_series(regime, seed=seed, base_price=base_price, n_days=180)
    df = s.to_dataframe()
    return extract_features(
        df=df,
        claimed_original_price=s.claimed_original_price,
        claimed_sale_price=s.claimed_sale_price,
        sale_date=s.sale_date,
        product_id=s.product_id,
    )


# ---------------------------------------------------------------------------
# Basic sanity checks
# ---------------------------------------------------------------------------

def test_extract_returns_price_features_for_all_regimes():
    from fdd.schema import PriceFeatures
    for regime in Regime:
        f = get_features(regime)
        assert isinstance(f, PriceFeatures)
        assert f.n_days_history == 180


def test_n_days_history_matches_dataframe():
    s = generate_series(Regime.GENUINE_DISCOUNT, seed=1, n_days=120)
    df = s.to_dataframe()
    f = extract_features(df, s.claimed_original_price, s.claimed_sale_price, s.sale_date)
    assert f.n_days_history == 120


def test_sale_price_percentile_in_range():
    for regime in Regime:
        f = get_features(regime)
        assert 0.0 <= f.sale_price_percentile <= 1.0, f"Out of range for {regime}"


def test_coefficient_of_variation_non_negative():
    for regime in Regime:
        f = get_features(regime)
        assert f.coefficient_of_variation >= 0.0


def test_volatility_label_valid():
    for regime in Regime:
        f = get_features(regime)
        assert f.volatility_label in ("low", "moderate", "high")


# ---------------------------------------------------------------------------
# Regime-specific expectations
# ---------------------------------------------------------------------------

def test_dark_pattern_has_high_spike():
    f = get_features(Regime.DARK_PATTERN)
    # Dark pattern always has a pre-sale price spike
    assert f.pre_sale_spike_pct > 0.10, (
        f"Expected spike > 10% for dark pattern, got {f.pre_sale_spike_pct:.2%}"
    )


def test_dark_pattern_short_original_hold():
    f = get_features(Regime.DARK_PATTERN)
    # The spike was artificial so original price was not held long
    assert f.days_original_price_held <= 30


def test_genuine_discount_sale_is_low():
    f = get_features(Regime.GENUINE_DISCOUNT)
    # Sale price should be below the historical median
    assert f.pct_below_median > 0.0, "Genuine discount: sale should be below median"
    # Sale price should sit low in the historical distribution
    assert f.sale_price_percentile < 0.50


def test_genuine_discount_no_large_spike():
    f = get_features(Regime.GENUINE_DISCOUNT)
    # Genuine discount: price doesn't spike before the sale
    assert f.pre_sale_spike_pct < 0.20


def test_stable_regime_low_volatility():
    f = get_features(Regime.STABLE)
    # Stable price history → low coefficient of variation
    assert f.coefficient_of_variation < 0.15


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_very_short_history():
    df = pd.DataFrame({
        "date": pd.date_range("2026-07-01", periods=10, freq="D"),
        "price": np.full(10, 1000.0),
    })
    f = extract_features(df, 1000.0, 800.0, "2026-07-09")
    assert f.n_days_history == 10
    assert f.sale_price_percentile >= 0.0


def test_empty_dataframe_raises():
    df = pd.DataFrame({"date": [], "price": []})
    with pytest.raises(ValueError, match="empty"):
        extract_features(df, 1000.0, 800.0, "2026-08-01")


def test_features_spike_pct_regime_ordering():
    """Dark pattern should have a higher spike % than genuine discount."""
    f_dark = get_features(Regime.DARK_PATTERN, seed=5)
    f_genuine = get_features(Regime.GENUINE_DISCOUNT, seed=5)
    assert f_dark.pre_sale_spike_pct > f_genuine.pre_sale_spike_pct
