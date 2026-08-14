"""
Core data contracts for the Fake Discount Detector.

NOTE: This is a STUB reconstructed from PROJECT_HANDOFF.md's documented
field list, for building/testing fdd/detection.py in isolation. Replace
with your actual fdd/schema.py before merging — field names must match
exactly or detection.py's attribute access will break.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional, Literal, Any


@dataclass
class PriceFeatures:
    """Engineered features for a single product's price history."""
    product_id: str
    n_days_history: int
    claimed_original_price: float
    claimed_sale_price: float
    sale_date: Optional[date]

    days_original_price_held: int          # how long the "original" price was stable before the sale
    pre_sale_spike_pct: float              # % price jumped in the run-up window before the sale
    sale_price_percentile: float           # where sale price sits in the product's historical price distribution (0-1)
    pct_below_median: float                # how far below the historical median the sale price is (can be negative)
    coefficient_of_variation: float        # std/mean of price history — volatility proxy
    volatility_label: Literal["low", "medium", "high"]
    trend_slope_per_day: float             # linear trend of price over time

    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoreFactor:
    """One named, explainable contributor to the suspicion score."""
    name: str
    description: str
    contribution: float   # signed contribution to suspicion_score, roughly in [-1, 1]


@dataclass
class DiscountAnalysisResult:
    """Final detector output for a single product."""
    product_id: str
    status: Literal["Genuine", "Suspicious", "Uncertain"]
    suspicion_score: float        # 0-1
    confidence: float             # 0-1
    volatility_score: float       # 0-1
    factors: list[ScoreFactor]
    explanation_text: str = ""
