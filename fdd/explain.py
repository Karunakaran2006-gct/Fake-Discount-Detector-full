"""
fdd/explain.py

PriceFeatures + DiscountAnalysisResult -> plain-language explanation text.

Template-driven: no ML, fully human-readable, per the design in PROJECT_HANDOFF.md.
Mutates result.explanation_text in place AND returns the string.
"""

from __future__ import annotations

from fdd.schema import PriceFeatures, DiscountAnalysisResult, DiscountStatus


# ---------------------------------------------------------------------------
# Sentence-level helpers
# ---------------------------------------------------------------------------

def _opening(features: PriceFeatures, result: DiscountAnalysisResult) -> str:
    pid = features.product_id
    n = len([f for f in result.factors if f.name != "isolation_forest_cross_check"])
    if result.status == DiscountStatus.SUSPICIOUS:
        return (
            f"This discount appears SUSPICIOUS. "
            f"The analysis detected {n} signal(s) suggesting the advertised "
            f"'original' price or the discount itself may be misleading."
        )
    if result.status == DiscountStatus.GENUINE:
        return (
            f"This discount appears GENUINE. "
            f"The pricing history supports the claimed original price and shows "
            f"a real, meaningful reduction at the time of sale."
        )
    return (
        f"The discount verdict is UNCERTAIN for {pid}. "
        f"Either the price history is too short ({features.n_days_history} days) "
        f"or the signals are too mixed to make a confident call either way."
    )


def _red_flags(result: DiscountAnalysisResult) -> list[str]:
    return [
        f.description
        for f in result.factors
        if f.contribution > 0 and f.name != "isolation_forest_cross_check"
    ]


def _green_flags(result: DiscountAnalysisResult) -> list[str]:
    return [
        f.description
        for f in result.factors
        if f.contribution < 0 and f.name != "isolation_forest_cross_check"
    ]


def _key_metrics(features: PriceFeatures) -> str:
    direction = "below" if features.pct_below_median >= 0 else "above"
    magnitude = abs(features.pct_below_median)
    return (
        f"The sale price sits at the {features.sale_price_percentile:.0%} percentile "
        f"of this product's historical prices and is {magnitude:.1%} {direction} the "
        f"historical median. Price volatility is {features.volatility_label} "
        f"(coefficient of variation = {features.coefficient_of_variation:.2f})."
    )


def _spike_sentence(features: PriceFeatures) -> str | None:
    pct = features.pre_sale_spike_pct
    if pct >= 0.35:
        return (
            f"Critically, the price surged {pct:.1%} in the days immediately before "
            f"the sale — a classic indicator of an artificially inflated 'original' price."
        )
    if pct >= 0.15:
        return (
            f"The price rose {pct:.1%} in the run-up to the sale, "
            f"above what normal price noise would explain."
        )
    if pct <= 0.05:
        return "No pre-sale price spike was detected."
    return None


def _hold_sentence(features: PriceFeatures) -> str:
    days = features.days_original_price_held
    if days <= 5:
        return (
            f"The 'original' price was only held for {days} day(s) before the sale — "
            f"far too brief to be a legitimate reference price."
        )
    if days <= 14:
        return (
            f"The claimed original price was held for {days} days before the sale, "
            f"shorter than a reliable reference period."
        )
    return (
        f"The claimed original price was maintained for {days} days before the sale, "
        f"suggesting it was a real, sustained price."
    )


def _confidence_note(features: PriceFeatures, result: DiscountAnalysisResult) -> str | None:
    if result.confidence < 0.5:
        return (
            f"Note: confidence is low ({result.confidence:.0%}) because the price history "
            f"covers only {features.n_days_history} days. A longer history would allow "
            f"a more reliable verdict."
        )
    return None


def _score_line(result: DiscountAnalysisResult) -> str:
    return (
        f"Suspicion score: {result.suspicion_score:.2f}/1.00 | "
        f"Volatility score: {result.volatility_score:.2f}/1.00 | "
        f"Confidence: {result.confidence:.2f}/1.00"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_explanation(
    features: PriceFeatures,
    result: DiscountAnalysisResult,
) -> str:
    """
    Build a plain-language explanation from features and detection result.

    Mutates result.explanation_text in place and also returns the string,
    so callers can use it either way.
    """
    paragraphs: list[str] = []

    # 1. Opening verdict
    paragraphs.append(_opening(features, result))

    # 2. Red flags
    reds = _red_flags(result)
    if reds:
        bullet_block = "\n".join(f"  • {r}" for r in reds)
        paragraphs.append("Red flags:\n" + bullet_block)

    # 3. Supporting factors
    greens = _green_flags(result)
    if greens:
        bullet_block = "\n".join(f"  • {g}" for g in greens)
        paragraphs.append("Factors supporting authenticity:\n" + bullet_block)

    # 4. Key metrics
    paragraphs.append(_key_metrics(features))

    # 5. Spike sentence (if interesting)
    spike = _spike_sentence(features)
    if spike:
        paragraphs.append(spike)

    # 6. Original price hold
    paragraphs.append(_hold_sentence(features))

    # 7. Confidence caveat
    note = _confidence_note(features, result)
    if note:
        paragraphs.append(note)

    # 8. Score line
    paragraphs.append(_score_line(result))

    text = "\n\n".join(paragraphs)
    result.explanation_text = text
    return text
