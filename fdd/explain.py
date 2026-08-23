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
    n = len([f for f in result.factors if f.name != "isolation_forest_cross_check"])
    if result.status == DiscountStatus.SUSPICIOUS:
        return (
            f"\u26a0\ufe0f This discount looks SUSPICIOUS. "
            f"We found {n} sign(s) that the advertised 'original' price or the "
            f"discount itself may not be what it seems."
        )
    if result.status == DiscountStatus.GENUINE:
        return (
            f"\u2705 This discount looks GENUINE. "
            f"The price history backs up the claimed original price and shows "
            f"a real, meaningful price drop at the time of the sale."
        )
    return (
        f"\u2753 The result is UNCERTAIN. "
        f"Either we don't have enough price history ({features.n_days_history} days) "
        f"or the signals are mixed — we can't call it either way with confidence."
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
    stability = {
        "low": "very stable",
        "moderate": "somewhat variable",
        "high": "quite erratic",
    }.get(features.volatility_label, features.volatility_label)
    rank = features.sale_price_percentile
    rank_desc = (
        "cheaper than almost all past prices" if rank <= 0.20
        else ("cheaper than most past prices" if rank <= 0.45
              else ("around the middle of past prices" if rank <= 0.60
                    else "still on the higher end of past prices"))
    )
    return (
        f"The sale price is {rank_desc}. "
        f"It is {magnitude:.1%} {direction} the typical price for this product. "
        f"The price history is {stability} overall."
    )


def _spike_sentence(features: PriceFeatures) -> str | None:
    pct = features.pre_sale_spike_pct
    if pct >= 0.35:
        return (
            f"Red flag: the price jumped {pct:.0%} in the days just before the sale. "
            f"This is a classic trick — inflate the price first, then 'discount' it."
        )
    if pct >= 0.15:
        return (
            f"The price rose {pct:.0%} in the run-up to the sale, "
            f"more than you'd expect from normal price noise."
        )
    if pct <= 0.05:
        return "No suspicious price jump was detected before the sale."
    return None


def _hold_sentence(features: PriceFeatures) -> str:
    days = features.days_original_price_held
    if days <= 5:
        return (
            f"The 'original' price was only shown for {days} day(s) before the sale. "
            f"That's way too short to count as a real reference price — it looks set up."
        )
    if days <= 14:
        return (
            f"The 'original' price was only maintained for {days} days before the sale. "
            f"That's shorter than you'd expect for a genuine long-standing price."
        )
    return (
        f"The 'original' price was held for {days} days before the sale — "
        f"long enough to be considered a real, established price."
    )


def _confidence_note(features: PriceFeatures, result: DiscountAnalysisResult) -> str | None:
    if result.confidence < 0.5:
        return (
            f"Note: we only have {features.n_days_history} days of price data, "
            f"which limits how sure we can be. A longer history would give a more reliable verdict."
        )
    return None


def _score_line(result: DiscountAnalysisResult) -> str:
    likelihood = "High" if result.suspicion_score > 0.55 else ("Low" if result.suspicion_score < 0.25 else "Medium")
    conf_label = "High" if result.confidence >= 0.75 else ("Medium" if result.confidence >= 0.5 else "Low")
    return (
        f"Fake-deal likelihood: {likelihood} ({result.suspicion_score:.0%}) | "
        f"Confidence in this result: {conf_label} ({result.confidence:.0%})"
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
        paragraphs.append("⚠️ Warning signs:\n" + bullet_block)

    # 3. Supporting factors
    greens = _green_flags(result)
    if greens:
        bullet_block = "\n".join(f"  • {g}" for g in greens)
        paragraphs.append("✅ Things that look fine:\n" + bullet_block)

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
