"""
fdd/gemini_explain.py

Uses Google Gemini API to generate a friendly, conversational explanation
and a clear user directive ("Should I buy this?") from PriceFeatures +
DiscountAnalysisResult.

Falls back silently to the template-based explanation (fdd/explain.py)
if no API key is set or the call fails.
"""

from __future__ import annotations

import os
from typing import Optional

from fdd.schema import PriceFeatures, DiscountAnalysisResult, DiscountStatus


# ---------------------------------------------------------------------------
# Build prompt
# ---------------------------------------------------------------------------

def _build_prompt(features: PriceFeatures, result: DiscountAnalysisResult) -> str:
    verdict = result.status.value
    flags = [f for f in result.factors if f.contribution > 0]
    greens = [f for f in result.factors if f.contribution < 0]

    flag_lines = "\n".join(f"- {f.description}" for f in flags) or "None"
    green_lines = "\n".join(f"- {f.description}" for f in greens) or "None"

    discount_pct = 0.0
    if features.claimed_original_price > 0:
        discount_pct = (
            (features.claimed_original_price - features.claimed_sale_price)
            / features.claimed_original_price * 100
        )

    return f"""You are a friendly, straight-talking shopping advisor. Your job is to explain a discount analysis result in plain English that anyone can understand — no jargon, no maths.

Here is the analysis data:

Product: {features.product_id}
Claimed original price: ₹{features.claimed_original_price:.0f}
Sale price: ₹{features.claimed_sale_price:.0f}
Advertised discount: {discount_pct:.0f}%
Days of price history available: {features.n_days_history}
Verdict: {verdict}
Fake-deal likelihood: {result.suspicion_score:.0%}
Confidence in this verdict: {result.confidence:.0%}
Days the "original" price was held before the sale: {features.days_original_price_held}
Price jump right before the sale: {features.pre_sale_spike_pct:.0%}
Sale price vs. typical price: {features.pct_below_median:.0%} below the usual price
Price history stability: {features.volatility_label}

Red flags found:
{flag_lines}

Things that look genuine:
{green_lines}

Write a response with EXACTLY these two sections (use these exact headings):

## What's going on
2-3 short paragraphs. Tell the user in plain conversational language what the price history shows, whether the "original" price seems real, and why the verdict is {verdict}. Mention specific numbers only if they're striking (e.g. "the price shot up 80% three days before the sale"). Don't use bullet points here — write as if you're texting a friend.

## Should you buy it?
One bold, direct recommendation. Start with one of: "✅ Go for it —", "🛑 Skip this one —", or "⚠️ Proceed with caution —". Then 1-2 sentences explaining what the shopper should actually DO. End with one practical tip (e.g. check the price on a tracker, wait for a better deal, compare with other sellers, etc.)

Keep the whole thing under 200 words. No headers other than the two above. No bullet points anywhere. No markdown tables. Sound human and relatable."""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def gemini_explain(
    features: PriceFeatures,
    result: DiscountAnalysisResult,
    api_key: Optional[str] = None,
    model: str = "gemini-1.5-flash",
) -> Optional[str]:
    """
    Call Gemini and return the explanation string, or None on failure.

    The returned string is NOT written into result.explanation_text — the
    caller (app.py) handles that so it can also display a separate directive.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        return None

    try:
        import google.generativeai as genai  # type: ignore

        genai.configure(api_key=key)
        model_obj = genai.GenerativeModel(model)
        resp = model_obj.generate_content(_build_prompt(features, result))
        return resp.text.strip()
    except Exception:
        return None


def parse_gemini_sections(text: str) -> tuple[str, str]:
    """
    Split the Gemini response into (what_is_going_on, should_you_buy_it).
    Returns (full_text, "") if sections can't be parsed.
    """
    if "## Should you buy it?" in text:
        parts = text.split("## Should you buy it?", 1)
        explanation = parts[0].replace("## What's going on", "").strip()
        directive = parts[1].strip()
        return explanation, directive
    return text, ""
