# Fake Discount Detector — Project Handoff / Context Doc

**Team:** Dhanya S. (IT) · Karunakaran R. (CSE)
**Purpose of this doc:** everything needed to continue building without re-deriving decisions from scratch. Written so any Claude session, or a human, can pick this up cold.

---

## 1. Project statement (official)

> Detect misleading discounts using historical pricing patterns instead of labels.
> 1. Accept historical price data.
> 2. Detect genuine vs suspicious discounts.
> 3. Measure price volatility to support decision.
>
> Pattern recognition focused. Must generate explanations.
>
> Outputs: Discount status · Volatility score · Plain-language explanation
> Deliverables: Data input · Decision output · README explaining detection logic

## 2. Scope decisions (agreed, don't relitigate)

- **In scope:** single-product price-history authenticity — was the claimed "original price" real and sustained, is the "sale price" genuinely low, how volatile is this product generally.
- **Out of scope:** marketplace/seller fraud, cross-seller comparison, live scraping, browser extension, backend API, database. This is a CSV-in → Streamlit analysis tool, not a BuyHatke competitor. Frame it in the README as "the detection engine a tool like BuyHatke would run on its backend" if asked to justify the comparison.
- **No supervised ML as the primary mechanism** — there is no real labeled dataset for "fake discount," and training on our own synthetic labels would just re-learn our rules in a less explainable form. Confirmed by the project statement itself ("instead of labels").
- **Approach: hybrid** — rule-based statistics as the core/primary signal, unsupervised anomaly detection (Isolation Forest) as a secondary cross-check. Supervised ML is an optional stretch goal only, to show "our rules resemble what a learned model would find" — never the thing the final decision depends on.
- **Three-state output, not binary:** `Genuine / Suspicious / Uncertain`. Uncertain covers short/insufficient history — forcing a binary call without enough data is technically weak and easy to challenge in a viva.
- **Volatility score and suspicion score are kept separate**, even though both feed the explanation. Don't conflate "this product's price is naturally volatile" with "this specific event looks manipulated."

## 3. Architecture (agreed)

Layered, each layer a pure-ish function with a fixed input/output contract:

```
Data Layer        → load/clean price history (CSV in, DataFrame out)
Feature Layer      → pure functions: series → engineered features (PriceFeatures)
Detection Layer    → features → status + score (rules + Isolation Forest cross-check) (DiscountAnalysisResult)
Explanation Layer  → features + result → plain-language reasons (fills DiscountAnalysisResult.explanation_text)
Presentation Layer → Streamlit: chart (Plotly) + status + score + explanation
```

No database, no backend API, no microservices — one Python package + one Streamlit app.

## 4. Tech stack (agreed, confirmed adequate)

```
Python
├── Pandas          → data handling
├── NumPy           → numerical calculations
├── SciPy           → stats if needed (barely used so far)
├── Scikit-learn     → anomaly detection (IsolationForest)
├── Plotly          → price graphs (interactive, annotatable, integrates with Streamlit)
├── Streamlit       → application UI
└── pytest          → testing (added on top of original list)
Git + GitHub        → collaboration
CSV                 → data format (input + synthetic output)
```
Deliberately **not** using: FastAPI/Flask, any database, deep learning/LSTM (no data for it, kills explainability), SHAP/LIME (core logic is already transparent, no black box to explain).

## 5. Two-person work split (agreed)

- **Dhanya (IT) — Data + Features owner:** data ingestion/cleaning, synthetic data generator, feature engineering functions. Output contract: `PriceFeatures`.
- **Karunakaran (CSE) — Detection + Explanation + Eval owner:** scoring/detection logic (rules + Isolation Forest), explanation generator, evaluation scripts against synthetic ground truth. Consumes `PriceFeatures`, produces `DiscountAnalysisResult`.
- **Streamlit UI:** thin layer, built together once the contract is stable.
- Branch per module (`feature/data-and-features`, `feature/detection-engine`, `feature/streamlit-ui`), PR-reviewed by the other person. GitHub Issues per function, not per day. pytest from the start, especially on the (pure-function) feature layer. Integrate early — wire the full pipeline end-to-end in week 1 even with stub layers, don't work in isolation for weeks.

## 6. Real dataset investigation (done)

Searched for a real Amazon price-history dataset. Finding, important to remember: **public "Amazon datasets" are almost all single-snapshot scrapes** (current price + MRP/actual price), not day-by-day time series. True price *history* datasets aren't freely available (real trackers like Keepa/BuyHatke build this via months of continuous scraping — infrastructure, not a downloadable file).

Used one real snapshot dataset (`JamilaAr/Amazon-Products-Sales-Dataset-2023`, Baby Products category, Amazon.in, 964 listings) — saved to `data/real_snapshot_reference.csv` — **not as detector input** (no time dimension) but to **calibrate the synthetic generator's price/discount ranges** so they're realistic, not arbitrary:
- `actual_price`: min=₹55, median=₹950, max=₹14,999
- `discount_pct`: median=40%, IQR≈24%–58%

Generator's `base_price` now drawn from a log-normal distribution (`rng.lognormal(mean=6.7, sigma=0.9)`) matching this median/long-tail shape, and `GENUINE_DISCOUNT` regime discount magnitude uses `rng.uniform(0.42, 0.76)` (i.e. 24–58% off) to match the real IQR.

**Honest limitation to state in README:** we don't have real multi-day price history; synthetic data (calibrated against real snapshot statistics) is our primary eval data. Real per-product time series would require manual daily tracking over weeks, which is a possible future extension, not something available as a ready dataset.

## 7. Pipeline progress

| Step | Status | File |
|---|---|---|
| 1. Contracts (schema) | ✅ done | `fdd/schema.py` |
| 2. Synthetic generator | ✅ done, tested, calibrated | `fdd/generator.py`, `tests/test_generator.py` |
| 3. Feature engineering | ⬜ **next** | `fdd/features.py` (not yet created) |
| 4. Detection + explanation | ⬜ | `fdd/detection.py`, `fdd/explain.py` |
| 5. Evaluation script | ⬜ | `fdd/evaluate.py` |
| 6. Streamlit UI | ⬜ | `app.py` |

## 8. Full current code

### `fdd/schema.py`

```python
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
```

### `fdd/generator.py`

```python
"""
Synthetic price history generator.

Produces (date, price) series under 4 regimes, each simulating a realistic
scenario a real e-commerce product's price history might show. Because we
generate these ourselves, we know the ground-truth label -- this is what
lets us evaluate the detector without needing real labeled data.

Regimes:
    STABLE           - flat price, small noise. A sale off this = genuine.
    GENUINE_DISCOUNT - price held steady for a long baseline, then a real,
                        sustained drop. The textbook "real sale".
    GRADUAL_DRIFT     - price slowly trends up or down over time (inflation,
                        demand changes). Not manipulation, just drift.
    DARK_PATTERN      - price is low/normal for a long time, then SPIKED up
                        just before the "sale", which discounts back down
                        close to the original normal price. The fake discount.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass
from enum import Enum


class Regime(str, Enum):
    STABLE = "stable"
    GENUINE_DISCOUNT = "genuine_discount"
    GRADUAL_DRIFT = "gradual_drift"
    DARK_PATTERN = "dark_pattern"


@dataclass
class SyntheticSeries:
    product_id: str
    regime: Regime
    dates: pd.DatetimeIndex
    prices: np.ndarray
    sale_date: str
    claimed_original_price: float
    claimed_sale_price: float
    ground_truth_genuine: bool  # True = should be judged Genuine, False = Suspicious

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({"date": self.dates, "price": self.prices})


def _noise(n, scale, rng):
    return rng.normal(0, scale, n)


def generate_series(
    regime: Regime,
    product_id: str = "SYN-0001",
    n_days: int = 180,
    base_price: float = 1000.0,
    noise_pct: float = 0.02,
    seed: int | None = None,
) -> SyntheticSeries:
    """Generate one synthetic price history for the given regime.

    n_days is total history length; the 'sale' event is placed near the end
    so there's a realistic pre-sale baseline to analyze.
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range(end=pd.Timestamp.today().normalize(), periods=n_days, freq="D")
    noise_scale = base_price * noise_pct

    sale_idx = n_days - 5  # sale happens 5 days before "today"

    if regime == Regime.STABLE:
        prices = base_price + _noise(n_days, noise_scale, rng)
        claimed_original = base_price
        claimed_sale = base_price * rng.uniform(0.95, 0.99)  # trivial/no real discount
        # Original price is real (price WAS stable there), but the "discount" is
        # negligible/cosmetic -> not a genuinely useful discount for the customer.
        genuine = False

    elif regime == Regime.GENUINE_DISCOUNT:
        prices = np.full(n_days, base_price, dtype=float)
        prices[sale_idx:] = base_price * rng.uniform(0.42, 0.76)  # real discounts: ~24%-58% off (matches real Amazon.in discount_pct IQR)
        prices += _noise(n_days, noise_scale, rng)
        claimed_original = base_price
        claimed_sale = prices[sale_idx]
        genuine = True

    elif regime == Regime.GRADUAL_DRIFT:
        drift = rng.choice([-1, 1]) * rng.uniform(0.3, 0.8)  # price per day drift
        trend = base_price + drift * np.arange(n_days)
        prices = trend + _noise(n_days, noise_scale, rng)
        claimed_original = prices[sale_idx - 1]
        claimed_sale = prices[sale_idx] * rng.uniform(0.96, 1.0)
        genuine = True  # slow organic drift, not manipulation

    elif regime == Regime.DARK_PATTERN:
        prices = np.full(n_days, base_price, dtype=float)
        spike_start = sale_idx - rng.integers(3, 10)  # spike appears 3-10 days before sale
        spike_price = base_price * rng.uniform(1.25, 1.6)
        prices[spike_start:sale_idx] = spike_price
        prices[sale_idx:] = base_price * rng.uniform(0.95, 1.05)  # "discount" lands ~back at normal
        prices += _noise(n_days, noise_scale, rng)
        claimed_original = spike_price
        claimed_sale = prices[sale_idx]
        genuine = False

    else:
        raise ValueError(f"Unknown regime: {regime}")

    return SyntheticSeries(
        product_id=product_id,
        regime=regime,
        dates=dates,
        prices=np.clip(prices, a_min=1.0, a_max=None),
        sale_date=str(dates[sale_idx].date()),
        claimed_original_price=round(float(claimed_original), 2),
        claimed_sale_price=round(float(claimed_sale), 2),
        ground_truth_genuine=genuine,
    )


def generate_dataset(n_per_regime: int = 10, seed: int = 42) -> list[SyntheticSeries]:
    """Generate a balanced labeled dataset across all 4 regimes. This is the
    ground-truth set used in evaluation (see fdd/evaluate.py).

    base_price and discount magnitudes are calibrated against a real Amazon.in
    product snapshot dataset (964 listings, Baby Products category, 2023):
        actual_price: min=55, median=950, max=14999
        discount_pct: median=40%, IQR=24%-58%
    This keeps our synthetic series realistic rather than arbitrary, even
    though that source dataset itself has no time dimension to run the
    detector on directly (single snapshot, not a price history).
    """
    rng = np.random.default_rng(seed)
    out = []
    pid = 1
    for regime in Regime:
        for _ in range(n_per_regime):
            s = generate_series(
                regime=regime,
                product_id=f"SYN-{pid:04d}",
                n_days=int(rng.integers(90, 240)),
                base_price=float(rng.lognormal(mean=6.7, sigma=0.9)),  # centers ~950, matches real median, long right tail like real data
                seed=int(rng.integers(0, 1_000_000)),
            )
            out.append(s)
            pid += 1
    return out


if __name__ == "__main__":
    # Quick smoke test / manual inspection
    for regime in Regime:
        s = generate_series(regime, seed=1)
        print(f"{regime.value:20s} sale_date={s.sale_date} "
              f"orig={s.claimed_original_price:>8.2f} sale={s.claimed_sale_price:>8.2f} "
              f"genuine={s.ground_truth_genuine}")
```

### `tests/test_generator.py`

```python
from fdd.generator import generate_series, generate_dataset, Regime


def test_all_regimes_generate():
    for regime in Regime:
        s = generate_series(regime, seed=1)
        assert len(s.prices) == 180
        assert s.claimed_original_price > 0
        assert s.claimed_sale_price > 0


def test_dark_pattern_has_spike():
    s = generate_series(Regime.DARK_PATTERN, seed=1, base_price=1000)
    baseline = s.prices[:20].mean()  # early history, before the spike
    assert s.prices.max() > baseline * 1.15  # spike should be clearly above baseline
    assert s.ground_truth_genuine is False


def test_genuine_discount_is_sustained():
    s = generate_series(Regime.GENUINE_DISCOUNT, seed=1, base_price=1000)
    assert s.claimed_sale_price < s.claimed_original_price * 0.9
    assert s.ground_truth_genuine is True


def test_generate_dataset_balanced():
    data = generate_dataset(n_per_regime=5)
    assert len(data) == 20
    regimes = [s.regime for s in data]
    for r in Regime:
        assert regimes.count(r) == 5
```

### `requirements.txt`

```
pandas
numpy
scipy
scikit-learn
plotly
streamlit
pytest
```

### `.gitignore`

```
venv/
__pycache__/
*.pyc
.pytest_cache/
.vscode/
*.egg-info/
.DS_Store
```

### `fdd/__init__.py`
Empty file, just makes `fdd/` an importable package.

## 9. Project folder structure (must match exactly)

```
fake-discount-detector/
├── fdd/
│   ├── __init__.py
│   ├── schema.py
│   └── generator.py
├── tests/
│   └── test_generator.py
├── data/
│   └── real_snapshot_reference.csv
├── requirements.txt
└── .gitignore
```

**Common mistake already hit once:** don't run loose duplicate files (e.g. `generator (1).py`) sitting outside `fdd/` via VS Code's F5/debugger — they won't have access to sibling modules once `features.py`/`detection.py` start doing `from fdd.schema import ...`. Always run via terminal from the project root: `python fdd/generator.py`, and always work inside the real cloned/extracted folder, not a stray downloaded copy.

## 10. Local setup / execution flow

```bash
cd fake-discount-detector
python -m venv venv
venv\Scripts\activate          # Windows. Mac/Linux: source venv/bin/activate
pip install -r requirements.txt

# then, every session:
python fdd/generator.py        # smoke test
python -m pytest tests/ -v     # full test suite, expect "4 passed"
```

VS Code: open the folder → `Ctrl+Shift+P` → "Python: Select Interpreter" → pick the `venv` one → use integrated terminal (`` Ctrl+` ``) for all commands above, not F5 on individual files (until an `app.py`/proper entrypoint exists for Streamlit later, which uses `streamlit run app.py`).

## 11. Verified output (confirmed working on Karunakaran's machine)

```
stable               sale_date=2026-08-06 orig= 1000.00 sale=  986.20 genuine=False
genuine_discount     sale_date=2026-08-06 orig= 1000.00 sale=  582.52 genuine=True
gradual_drift        sale_date=2026-08-06 orig=  853.61 sale=  817.44 genuine=True
dark_pattern         sale_date=2026-08-06 orig= 1582.66 sale=  977.17 genuine=False
```
`pytest tests/ -v` → 4 passed.

## 12. Next step (Step 3): feature engineering

Goal: `fdd/features.py` with a function like `extract_features(df: pd.DataFrame, claimed_original_price, claimed_sale_price, sale_date, product_id) -> PriceFeatures` that computes:
- `days_original_price_held` — consecutive days before sale_date price sat near claimed_original_price
- `pre_sale_spike_pct` — % jump in short pre-sale window vs. prior baseline (this is the core dark-pattern signal)
- `sale_price_percentile` — percentile rank of claimed_sale_price within full historical distribution
- `pct_below_median` — % below historical median
- `coefficient_of_variation` + `volatility_label` (low/moderate/high, needs threshold choice — document rationale)
- `trend_slope_per_day` — simple linear regression slope over full history

This is nominally Dhanya's module per the work split (§5), but Claude will build a working version to unblock both — test it against `generate_dataset()` output before wiring detection logic on top, and check features look meaningfully different across the 4 regimes.

After that: Step 4 (`detection.py` — turn features into `DiscountAnalysisResult` via rules + Isolation Forest cross-check) and `explain.py` (template-based plain-language text per `ScoreFactor`), Step 5 (`evaluate.py` — precision/recall against `ground_truth_genuine`), Step 6 (Streamlit `app.py`).

---
*End of handoff doc. Paste this whole file back into a new Claude conversation (or continue the same one) to resume with full context.*
