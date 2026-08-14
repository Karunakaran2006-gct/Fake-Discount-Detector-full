"""
fdd/features.py

Raw price history DataFrame (date + price) -> PriceFeatures.

All logic is pure computation — no I/O, no side effects.
Each helper is independently testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from fdd.schema import PriceFeatures


# ---------------------------------------------------------------------------
# Tunable parameters (mirror the thresholds used in detection.py)
# ---------------------------------------------------------------------------

PRICE_TOLERANCE: float = 0.05   # within 5% of claimed_original counts as "held"
SPIKE_WINDOW_DAYS: int = 14     # days immediately before sale checked for spike
MIN_BASELINE_DAYS: int = 7      # minimum baseline days needed to compute spike

CV_LOW_THRESHOLD: float = 0.05
CV_HIGH_THRESHOLD: float = 0.30


# ---------------------------------------------------------------------------
# Internal helpers (pure functions)
# ---------------------------------------------------------------------------

def _parse_df(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure 'date' is datetime, sort ascending, drop NaN prices."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["price"]).sort_values("date").reset_index(drop=True)
    return df


def _days_original_price_held(
    pre_sale_prices: pd.Series,
    claimed_original_price: float,
    tolerance: float = PRICE_TOLERANCE,
) -> int:
    """
    Consecutive days (counting backwards from the sale) where the price
    stayed within `tolerance` of `claimed_original_price`.

    This tells us whether the 'original' price was real and sustained,
    or was set artificially just before the sale.
    """
    if pre_sale_prices.empty:
        return 0
    lo = claimed_original_price * (1.0 - tolerance)
    hi = claimed_original_price * (1.0 + tolerance)
    in_range = (pre_sale_prices >= lo) & (pre_sale_prices <= hi)
    count = 0
    for flag in reversed(in_range.tolist()):
        if flag:
            count += 1
        else:
            break
    return count


def _pre_sale_spike_pct(
    pre_sale_prices: pd.Series,
    spike_window: int = SPIKE_WINDOW_DAYS,
    min_baseline: int = MIN_BASELINE_DAYS,
) -> float:
    """
    % change in mean price between the spike window (immediately before the
    sale) and the baseline (everything before the spike window).

    Positive value = price went UP before the sale (suspicious).
    Returns 0.0 when there is not enough data.
    """
    n = len(pre_sale_prices)
    if n < 2:
        return 0.0

    if n < spike_window + min_baseline:
        # not enough days: split in half
        split = max(1, n // 2)
        baseline = pre_sale_prices.iloc[:split]
        window = pre_sale_prices.iloc[split:]
    else:
        window = pre_sale_prices.iloc[-spike_window:]
        baseline = pre_sale_prices.iloc[:-spike_window]

    baseline_mean = baseline.mean()
    if baseline_mean == 0.0:
        return 0.0
    return float((window.mean() - baseline_mean) / baseline_mean)


def _sale_price_percentile(all_prices: pd.Series, claimed_sale_price: float) -> float:
    """
    Percentile rank of the sale price within the full price history.
    Returns a value in [0.0, 1.0].  High = sale price is not actually cheap.
    """
    pct = stats.percentileofscore(all_prices.tolist(), claimed_sale_price, kind="rank")
    return round(pct / 100.0, 4)


def _pct_below_median(all_prices: pd.Series, claimed_sale_price: float) -> float:
    """
    (median - sale_price) / median.
    Positive → sale price is below the median (good deal).
    Negative → sale price is above the median (not a real discount).
    """
    median = float(all_prices.median())
    if median == 0.0:
        return 0.0
    return round((median - claimed_sale_price) / median, 4)


def _coefficient_of_variation(all_prices: pd.Series) -> float:
    """std / mean of the full price history. Measures price volatility."""
    mean = float(all_prices.mean())
    if mean == 0.0:
        return 0.0
    return round(float(all_prices.std()) / mean, 4)


def _volatility_label(cv: float) -> str:
    """Bin the coefficient of variation into a human-readable label."""
    if cv < CV_LOW_THRESHOLD:
        return "low"
    if cv >= CV_HIGH_THRESHOLD:
        return "high"
    return "moderate"


def _trend_slope(all_prices: pd.Series) -> float:
    """Linear regression slope of price over time (price units per day)."""
    n = len(all_prices)
    if n < 2:
        return 0.0
    x = np.arange(n, dtype=float)
    slope, _ = np.polyfit(x, all_prices.values.astype(float), 1)
    return round(float(slope), 4)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_features(
    df: pd.DataFrame,
    claimed_original_price: float,
    claimed_sale_price: float,
    sale_date: str,
    product_id: str = "UNKNOWN",
) -> PriceFeatures:
    """
    Compute all PriceFeatures from a raw price-history DataFrame.

    Parameters
    ----------
    df : DataFrame with columns 'date' (any parseable date format) and
         'price' (numeric).
    claimed_original_price : The 'was' / MRP price shown by the retailer.
    claimed_sale_price     : The advertised discounted price.
    sale_date              : ISO date string of the discount event, e.g. '2026-08-06'.
    product_id             : Optional product identifier passed through to the result.

    Returns
    -------
    PriceFeatures ready for fdd.detection.analyze().
    """
    df = _parse_df(df)
    if df.empty:
        raise ValueError("Price history DataFrame is empty after cleaning.")

    sale_ts = pd.Timestamp(sale_date)
    pre_sale = df[df["date"] < sale_ts]["price"].reset_index(drop=True)
    all_prices = df["price"]

    cv = _coefficient_of_variation(all_prices)

    return PriceFeatures(
        product_id=product_id,
        n_days_history=len(df),
        claimed_original_price=float(claimed_original_price),
        claimed_sale_price=float(claimed_sale_price),
        sale_date=sale_date,
        days_original_price_held=_days_original_price_held(
            pre_sale, claimed_original_price
        ),
        pre_sale_spike_pct=round(_pre_sale_spike_pct(pre_sale), 4),
        sale_price_percentile=_sale_price_percentile(all_prices, claimed_sale_price),
        pct_below_median=_pct_below_median(all_prices, claimed_sale_price),
        coefficient_of_variation=cv,
        volatility_label=_volatility_label(cv),
        trend_slope_per_day=_trend_slope(all_prices),
    )
