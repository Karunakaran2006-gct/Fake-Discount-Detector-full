# Fake Discount Detector — Project Status for Claude

## Project goal

Detect misleading discounts by analyzing historical pricing patterns instead of relying on labels.

The detector is designed to answer:
- Was the claimed original price real and sustained?
- Was the sale price actually low?
- Did the price spike right before the sale in a way that looks manipulative?
- How volatile is the product’s pricing normally?

Expected outputs:
- Discount status: Genuine / Suspicious / Uncertain
- Suspicion score
- Volatility score
- Plain-language explanation

---

## Current state of the repo

### Completed

1. Project concept documented in [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md)
2. Core data contracts defined in [fdd/schema.py](fdd/schema.py)
3. Synthetic price history generator implemented in [fdd/generator.py](fdd/generator.py)
4. Unit tests created in [tests/test_generator.py](tests/test_generator.py)
5. Real snapshot dataset stored in [data/real_snapshot_reference.csv](data/real_snapshot_reference.csv)

### Not yet implemented

The following modules are still pending according to the project plan:
- feature engineering layer
- detection logic
- explanation text generation
- evaluation script
- Streamlit app UI

---

## Architecture decisions already made

The project uses a layered design:

- Data layer: load/clean price history
- Feature layer: transform series into numeric features
- Detection layer: classify Genuine / Suspicious / Uncertain
- Explanation layer: convert scores into plain-language narrative
- Presentation layer: UI for showing chart + verdict + explanation

Important design decisions recorded in [PROJECT_HANDOFF.md](PROJECT_HANDOFF.md):
- Rule-based statistics are the primary mechanism
- Isolation Forest is a secondary cross-check, not the final decision-maker
- Three-state output is preferred over binary classification
- Volatility score and suspicion score are kept separate
- Synthetic data is used as the main evaluation proxy because real multi-day price histories are not freely available

---

## Synthetic data design

The generator in [fdd/generator.py](fdd/generator.py) creates artificial product price histories under four regimes:

1. Stable
   - Price is mostly flat with small noise
   - Discount is tiny or cosmetic
   - Should not be treated as a meaningful sale

2. Genuine discount
   - Price stays stable for a long time
   - Then drops significantly and stays low
   - This is the real-sale scenario

3. Gradual drift
   - Price slowly rises or falls over time
   - This is not manipulation

4. Dark pattern
   - Price sits at a normal level
   - Then spikes just before the sale
   - Then returns close to the normal level
   - This is the fake-discount pattern

The generator is calibrated against real snapshot statistics from Amazon product data, but the snapshot file is not a true time-series input.

---

## Data contract summary

The project defines these core objects in [fdd/schema.py](fdd/schema.py):

### PriceFeatures
Represents engineered features for a product history:
- product_id
- n_days_history
- claimed_original_price
- claimed_sale_price
- sale_date
- days_original_price_held
- pre_sale_spike_pct
- sale_price_percentile
- pct_below_median
- coefficient_of_variation
- volatility_label
- trend_slope_per_day
- extra

### DiscountAnalysisResult
Final detector output:
- product_id
- status
- suspicion_score
- confidence
- volatility_score
- factors
- explanation_text

### ScoreFactor
One named factor contributing to the suspicion score, for example:
- pre_sale_spike
- high original-price inflation
- sale price not meaningfully below typical range

---

## Current test status

The current test suite in [tests/test_generator.py](tests/test_generator.py) validates that:
- all regimes generate correctly
- dark-pattern series contain a spike
- genuine-discount series show a real drop
- the dataset generator produces balanced regime counts

The test run has passed successfully in the current environment.

---

## Important project note

The project handoff explicitly states that the real dataset in [data/real_snapshot_reference.csv](data/real_snapshot_reference.csv) is a single snapshot dataset and not a real multi-day price history dataset.

This means:
- it helps calibrate realistic price ranges and discount percentages
- it is not enough by itself to run the detector end-to-end
- the detector will need a true time-series historical price table later

---

## Recommended next implementation steps

To complete the project, the next modules should be created in this order:

1. [fdd/features.py]
   - compute historical features from a price series

2. [fdd/detection.py]
   - combine rule-based logic with Isolation Forest cross-check
   - return DiscountAnalysisResult

3. [fdd/explain.py]
   - build plain-language explanation text from factors and scores

4. [fdd/evaluate.py]
   - measure detector performance against synthetic ground truth

5. [app.py]
   - optional Streamlit UI for visualization and display

---

## Working assumptions for continuations

- The detector should be explainable, not black-box driven.
- The final decision should be three-state, not binary.
- Real product histories are preferred over synthetic data, but the project has to rely on synthetic generation for now because real time-series datasets are difficult to obtain.
- The generator and schema are already finished enough to serve as the foundation for the next implementation stage.

---

## One-sentence summary for the next Claude session

This repo already contains the project definition, schema, synthetic data generator, and tests; the remaining work is to build the feature engineering, detection rules, explanation logic, evaluation pipeline, and UI on top of this foundation.
