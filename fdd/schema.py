"""
Core data contracts for the Fake Discount Detector pipeline.

Pipeline:
    raw price history --> [features.py] --> PriceFeatures
    PriceFeatures      --> [detection.py] --> DiscountAnalysisResult
    DiscountAnalysisResult --> [explain.py] --> explanation text (attached to result)
"""

from dataclasses import dataclass, field
from enum import Enum


class DiscountStatus(str, Enum):
    GENUINE = "Genuine"
    SUSPICIOUS = "Suspicious"
    UNCERTAIN = "Uncertain"  # not enough history / weak signal either way


@dataclass
class PriceFeatures:
    """Output of the feature engineering layer. Pure numbers, no verdicts here."""

    # -- context --
    product_id: str
    n_days_history: int          # how many days of price history we actually have
    claimed_original_price: float
    claimed_sale_price: float
    sale_date: str                # ISO date string of the discount event

    # -- "was the original price real?" --
    days_original_price_held: int   # consecutive days price sat at/near claimed_original_price before sale
    pre_sale_spike_pct: float       # % jump in price in the short window right before sale, vs prior baseline

    # -- "is the sale price actually low?" --
    sale_price_percentile: float    # where claimed_sale_price sits in the historical price distribution (0-100)
    pct_below_median: float         # % sale price is below the historical median

    # -- "how volatile is this product's pricing?" --
    coefficient_of_variation: float  # std/mean of price over full history
    volatility_label: str            # "low" | "moderate" | "high"

    # -- trend --
    trend_slope_per_day: float       # simple linear trend of price over history

    extra: dict = field(default_factory=dict)  # escape hatch, avoid schema churn


@dataclass
class ScoreFactor:
    """One named, human-readable contributor to the final suspicion score."""

    name: str            # e.g. "pre_sale_spike"
    description: str     # e.g. "Price jumped 42% just 6 days before the sale"
    contribution: float  # signed contribution to suspicion score, e.g. +0.3 or -0.1


@dataclass
class DiscountAnalysisResult:
    """Final output of the detection layer, consumed by explanation + UI layers."""

    product_id: str
    status: DiscountStatus
    suspicion_score: float       # 0 (genuine) to 1 (highly suspicious)
    confidence: float            # 0-1, how much we trust this verdict (low if little history)
    volatility_score: float      # 0-1, independent of suspicion
    factors: list[ScoreFactor] = field(default_factory=list)
    explanation_text: str = ""   # filled in by explain.py
