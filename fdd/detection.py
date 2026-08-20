"""
fdd/detection.py

PriceFeatures -> DiscountAnalysisResult

Design (per PROJECT_HANDOFF.md):
- Rule-based scoring is PRIMARY. Each rule is an explainable ScoreFactor.
- Isolation Forest is a SECONDARY cross-check signal only, not the decision-maker.
- Confidence is gated by n_days_history — short histories can't earn a
  confident Genuine/Suspicious verdict, they fall back to Uncertain.
- Suspicion score and volatility score are computed independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fdd.schema import PriceFeatures, DiscountAnalysisResult, ScoreFactor, DiscountStatus


# ---------------------------------------------------------------------------
# Tunable thresholds — kept as module-level constants so they're easy to
# calibrate later against real data without touching the logic.
# ---------------------------------------------------------------------------

# -- suspicion rule thresholds --
SPIKE_PCT_THRESHOLD = 0.15          # >15% pre-sale price jump is a red flag
SPIKE_PCT_HARD = 0.35               # >35% is a strong red flag

SHORT_HOLD_DAYS_THRESHOLD = 14      # "original" price held < 14 days is suspicious
SHORT_HOLD_DAYS_HARD = 5            # < 5 days is a strong red flag

HIGH_PERCENTILE_THRESHOLD = 0.60    # sale price still in top 40% of history = not really "low"
HIGH_PERCENTILE_HARD = 0.80

LOW_PCT_BELOW_MEDIAN_THRESHOLD = 0.05  # sale barely below median (<5%) is suspicious

MIN_DAYS_HISTORY_FOR_CONFIDENCE = 30   # below this, confidence is capped
LOW_HISTORY_CONFIDENCE_CAP = 0.45

# -- status thresholds (applied to suspicion_score) --
SUSPICIOUS_THRESHOLD = 0.55
GENUINE_THRESHOLD = 0.25
# scores between GENUINE_THRESHOLD and SUSPICIOUS_THRESHOLD are ambiguous
# and, combined with low confidence, push toward "Uncertain"

UNCERTAIN_CONFIDENCE_FLOOR = 0.5    # below this confidence, verdict becomes Uncertain
                                     # regardless of where suspicion_score landed

# -- volatility score thresholds (derived from coefficient_of_variation) --
CV_LOW = 0.05
CV_HIGH = 0.30


# ---------------------------------------------------------------------------
# Suspicion scoring — rule-based
# ---------------------------------------------------------------------------

def _score_pre_sale_spike(f: PriceFeatures) -> Optional[ScoreFactor]:
    pct = f.pre_sale_spike_pct
    if pct >= SPIKE_PCT_HARD:
        return ScoreFactor(
            name="pre_sale_spike",
            description=f"Price spiked {pct:.0%} shortly before the sale — classic fake-discount pattern.",
            contribution=0.40,
        )
    if pct >= SPIKE_PCT_THRESHOLD:
        return ScoreFactor(
            name="pre_sale_spike",
            description=f"Price rose {pct:.0%} in the run-up to the sale, higher than normal fluctuation.",
            contribution=0.20,
        )
    if pct <= 0.05:
        return ScoreFactor(
            name="pre_sale_spike",
            description="No significant pre-sale price increase detected.",
            contribution=-0.10,
        )
    return None


def _score_short_hold(f: PriceFeatures) -> Optional[ScoreFactor]:
    days = f.days_original_price_held
    if days <= SHORT_HOLD_DAYS_HARD:
        return ScoreFactor(
            name="short_original_price_hold",
            description=f"'Original' price was only held for {days} day(s) before the sale — too brief to be a real reference price.",
            contribution=0.30,
        )
    if days <= SHORT_HOLD_DAYS_THRESHOLD:
        return ScoreFactor(
            name="short_original_price_hold",
            description=f"'Original' price was held for only {days} days, shorter than a typical stable reference period.",
            contribution=0.15,
        )
    if days >= 21:
        return ScoreFactor(
            name="long_original_price_hold",
            description=f"'Original' price was held stably for {days} days before the sale.",
            contribution=-0.10,
        )
    return None


def _score_sale_price_percentile(f: PriceFeatures) -> Optional[ScoreFactor]:
    pctl = f.sale_price_percentile
    if pctl >= HIGH_PERCENTILE_HARD:
        return ScoreFactor(
            name="sale_price_not_low",
            description=f"'Sale' price sits at the {pctl:.0%} percentile of this product's historical prices — it isn't actually cheap.",
            contribution=0.35,
        )
    if pctl >= HIGH_PERCENTILE_THRESHOLD:
        return ScoreFactor(
            name="sale_price_not_low",
            description=f"'Sale' price sits at the {pctl:.0%} percentile of history — only mildly below typical prices.",
            contribution=0.18,
        )
    if pctl <= 0.20:
        return ScoreFactor(
            name="sale_price_genuinely_low",
            description=f"Sale price sits at the {pctl:.0%} percentile of history — genuinely low relative to past prices.",
            contribution=-0.15,
        )
    return None


def _score_pct_below_median(f: PriceFeatures) -> Optional[ScoreFactor]:
    pct = f.pct_below_median
    if pct < LOW_PCT_BELOW_MEDIAN_THRESHOLD:
        return ScoreFactor(
            name="minimal_discount_vs_median",
            description=f"Sale price is only {pct:.0%} below the historical median price.",
            contribution=0.08,
        )
    if pct > 0.15:
        return ScoreFactor(
            name="deep_discount_vs_median",
            description=f"Sale price is {pct:.0%} below the historical median price — a substantial discount.",
            contribution=-0.15,
        )
    return None


def _score_trend(f: PriceFeatures) -> Optional[ScoreFactor]:
    # A strong upward trend followed by a "discount" back to baseline is
    # a softer version of the spike pattern — catch cases spike_pct might miss.
    if f.trend_slope_per_day > 0 and f.pre_sale_spike_pct >= SPIKE_PCT_THRESHOLD:
        return ScoreFactor(
            name="rising_trend_plus_spike",
            description="Price was already trending upward on top of the pre-sale spike, compounding the manipulation signal.",
            contribution=0.10,
        )
    return None


_SUSPICION_RULES = [
    _score_pre_sale_spike,
    _score_short_hold,
    _score_sale_price_percentile,
    _score_pct_below_median,
    _score_trend,
]


def compute_suspicion(f: PriceFeatures) -> tuple[float, list[ScoreFactor]]:
    """Run all rules, sum contributions, clip to [0, 1]."""
    factors: list[ScoreFactor] = []
    raw = 0.0
    for rule in _SUSPICION_RULES:
        result = rule(f)
        if result is not None:
            factors.append(result)
            raw += result.contribution

    # baseline 0.5 keeps a "no signal either way" product near the middle,
    # then rule contributions push it up (suspicious) or down (genuine)
    score = 0.5 + raw
    score = max(0.0, min(1.0, score))
    return score, factors


# ---------------------------------------------------------------------------
# Volatility scoring — independent of suspicion
# ---------------------------------------------------------------------------

def compute_volatility_score(f: PriceFeatures) -> float:
    cv = f.coefficient_of_variation
    if cv <= CV_LOW:
        return 0.0 + (cv / CV_LOW) * 0.2  # 0.0 - 0.2
    if cv >= CV_HIGH:
        return 1.0
    # linear interpolation between low and high anchors
    span = CV_HIGH - CV_LOW
    return 0.2 + ((cv - CV_LOW) / span) * 0.8


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------

def compute_confidence(f: PriceFeatures) -> float:
    """
    Confidence scales with history length. Short histories get capped low
    so the status-assignment step can honestly fall back to "Uncertain"
    instead of guessing.
    """
    if f.n_days_history <= 0:
        return 0.0
    if f.n_days_history >= MIN_DAYS_HISTORY_FOR_CONFIDENCE:
        # more history keeps nudging confidence up, saturating near 1.0
        extra = min(1.0, (f.n_days_history - MIN_DAYS_HISTORY_FOR_CONFIDENCE) / 60)
        return min(1.0, 0.75 + 0.25 * extra)
    # sub-linear ramp up to the cap for histories shorter than the minimum
    frac = f.n_days_history / MIN_DAYS_HISTORY_FOR_CONFIDENCE
    return frac * LOW_HISTORY_CONFIDENCE_CAP


# ---------------------------------------------------------------------------
# Status assignment
# ---------------------------------------------------------------------------

def assign_status(suspicion_score: float, confidence: float) -> DiscountStatus:
    if confidence < UNCERTAIN_CONFIDENCE_FLOOR:
        return DiscountStatus.UNCERTAIN
    if suspicion_score >= SUSPICIOUS_THRESHOLD:
        return DiscountStatus.SUSPICIOUS
    if suspicion_score <= GENUINE_THRESHOLD:
        return DiscountStatus.GENUINE
    return DiscountStatus.UNCERTAIN


# ---------------------------------------------------------------------------
# Isolation Forest cross-check (secondary signal)
# ---------------------------------------------------------------------------

@dataclass
class IsolationForestResult:
    is_outlier: bool
    anomaly_score: float  # higher = more anomalous


def isolation_forest_cross_check(
    target: PriceFeatures,
    reference_population: list[PriceFeatures],
    contamination: float = 0.1,
    random_state: int = 42,
) -> Optional[IsolationForestResult]:
    """
    Flags whether `target` is an outlier relative to `reference_population`
    across the numeric feature vector. Requires sklearn and a reasonably
    sized reference population (>= 10) to be meaningful; returns None
    otherwise so callers can skip the cross-check gracefully.

    This is NOT used to set status directly — it's surfaced as an extra
    factor/flag so a human (or the explanation layer) can see when the
    rule-based verdict and the anomaly-detection verdict disagree.
    """
    if len(reference_population) < 10:
        return None

    try:
        from sklearn.ensemble import IsolationForest
        import numpy as np
    except ImportError:
        return None

    def vec(f: PriceFeatures) -> list[float]:
        return [
            f.pre_sale_spike_pct,
            f.days_original_price_held,
            f.sale_price_percentile,
            f.pct_below_median,
            f.coefficient_of_variation,
            f.trend_slope_per_day,
        ]

    X = np.array([vec(f) for f in reference_population])
    model = IsolationForest(contamination=contamination, random_state=random_state)
    model.fit(X)

    target_vec = np.array([vec(target)])
    pred = model.predict(target_vec)[0]          # -1 = outlier, 1 = inlier
    raw_score = model.score_samples(target_vec)[0]  # lower = more anomalous

    # normalize raw_score (~[-0.5, 0.5] typically) into a 0-1 "anomaly-ness"
    anomaly_score = max(0.0, min(1.0, 0.5 - raw_score))

    return IsolationForestResult(
        is_outlier=(pred == -1),
        anomaly_score=anomaly_score,
    )


# ---------------------------------------------------------------------------
# Top-level entry point
# ---------------------------------------------------------------------------

def analyze(
    features: PriceFeatures,
    reference_population: Optional[list[PriceFeatures]] = None,
) -> DiscountAnalysisResult:
    """
    Main entry point: PriceFeatures -> DiscountAnalysisResult.

    If `reference_population` is supplied (e.g. the full synthetic dataset,
    or all products in the same category), an Isolation Forest cross-check
    is run and appended as an extra ScoreFactor — informational only, it
    does not change suspicion_score or status.
    """
    suspicion_score, factors = compute_suspicion(features)
    volatility_score = compute_volatility_score(features)
    confidence = compute_confidence(features)
    status = assign_status(suspicion_score, confidence)

    if reference_population:
        if_result = isolation_forest_cross_check(features, reference_population)
        if if_result is not None:
            agreement = (
                "agrees with" if (if_result.is_outlier == (status == "Suspicious"))
                else "disagrees with"
            )
            factors.append(ScoreFactor(
                name="isolation_forest_cross_check",
                description=(
                    f"Isolation Forest {'flags this as an outlier' if if_result.is_outlier else 'does not flag this as an outlier'} "
                    f"(anomaly score {if_result.anomaly_score:.2f}) — {agreement} the rule-based verdict."
                ),
                contribution=0.0,  # informational only, per design: secondary not primary
            ))

    return DiscountAnalysisResult(
        product_id=features.product_id,
        status=status,
        suspicion_score=round(suspicion_score, 4),
        confidence=round(confidence, 4),
        volatility_score=round(volatility_score, 4),
        factors=factors,
        explanation_text="",  # filled in by fdd/explain.py later
    )
