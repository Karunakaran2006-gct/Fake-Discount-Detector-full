"""
fdd/evaluate.py

Full pipeline evaluation: generator -> features -> detection -> explanation.
Measures precision / recall / accuracy against synthetic ground-truth labels.

Run:
    python fdd/evaluate.py
    python fdd/evaluate.py --n 20        # 20 products per regime
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd

from fdd.generator import generate_dataset, SyntheticSeries, Regime
from fdd.features import extract_features
from fdd.detection import analyze
from fdd.explain import generate_explanation
from fdd.schema import DiscountStatus


# ---------------------------------------------------------------------------
# Evaluation row
# ---------------------------------------------------------------------------

@dataclass
class EvalRow:
    product_id: str
    regime: str
    ground_truth_genuine: bool
    predicted_status: str
    suspicion_score: float
    confidence: float
    volatility_score: float
    correct: bool | None   # None = Uncertain prediction (neither correct nor wrong)


# ---------------------------------------------------------------------------
# Core evaluation loop
# ---------------------------------------------------------------------------

def run_pipeline(series: SyntheticSeries) -> EvalRow:
    """Run the full stack on one synthetic series, return an EvalRow."""
    df = series.to_dataframe()

    features = extract_features(
        df=df,
        claimed_original_price=series.claimed_original_price,
        claimed_sale_price=series.claimed_sale_price,
        sale_date=series.sale_date,
        product_id=series.product_id,
    )

    result = analyze(features)
    generate_explanation(features, result)

    gt_genuine = series.ground_truth_genuine

    status_val = result.status.value if hasattr(result.status, "value") else str(result.status)

    if status_val == "Uncertain":
        correct = None   # uncertain — can't score as right or wrong
    elif status_val == "Genuine":
        correct = gt_genuine
    else:  # Suspicious
        correct = not gt_genuine

    return EvalRow(
        product_id=series.product_id,
        regime=series.regime.value,
        ground_truth_genuine=gt_genuine,
        predicted_status=status_val,
        suspicion_score=result.suspicion_score,
        confidence=result.confidence,
        volatility_score=result.volatility_score,
        correct=correct,
    )


def evaluate(n_per_regime: int = 10, seed: int = 42, verbose: bool = True) -> pd.DataFrame:
    """
    Evaluate the detector against a balanced synthetic dataset.

    Parameters
    ----------
    n_per_regime : products generated per regime (total = 4 × n)
    seed         : RNG seed for reproducibility
    verbose      : print the report to stdout

    Returns
    -------
    DataFrame with one row per product containing all metrics.
    """
    dataset = generate_dataset(n_per_regime=n_per_regime, seed=seed)
    rows = [run_pipeline(s) for s in dataset]
    df = pd.DataFrame([vars(r) for r in rows])

    if verbose:
        _print_report(df, n_per_regime)

    return df


# ---------------------------------------------------------------------------
# Report printer
# ---------------------------------------------------------------------------

def _print_report(df: pd.DataFrame, n_per_regime: int) -> None:
    sep = "=" * 72

    print(f"\n{sep}")
    print("  FAKE DISCOUNT DETECTOR - EVALUATION REPORT")
    print(f"  {len(df)} products  ({n_per_regime} per regime x 4 regimes)")
    print(sep)

    # Per-product table
    print(f"\n{'Product':<12} {'Regime':<22} {'GT':<12} {'Predicted':<12} {'OK':<5} {'Susp':>6} {'Conf':>6}")
    print("-" * 72)
    for _, row in df.iterrows():
        gt = "Genuine" if row["ground_truth_genuine"] else "Suspicious"
        ok = "OK" if row["correct"] is True else ("FAIL" if row["correct"] is False else "?")
        print(
            f"{row['product_id']:<12} {row['regime']:<22} {gt:<12} "
            f"{row['predicted_status']:<12} {ok:<6} "
            f"{row['suspicion_score']:>6.3f} {row['confidence']:>6.3f}"
        )

    # Accuracy (excluding Uncertain)
    decided = df[df["correct"].notna()]
    uncertain_count = len(df) - len(decided)
    accuracy = decided["correct"].mean() if len(decided) > 0 else float("nan")

    print("\n" + "-" * 72)
    print(f"  Uncertain predictions: {uncertain_count}/{len(df)}")
    print(f"  Accuracy (decided only): {accuracy:.1%}  ({decided['correct'].sum():.0f}/{len(decided)} correct)")

    # Per-regime accuracy
    print("\n  Accuracy by regime:")
    for regime, grp in df.groupby("regime"):
        decided_grp = grp[grp["correct"].notna()]
        if len(decided_grp) == 0:
            print(f"    {regime:<22}: all Uncertain")
            continue
        acc = decided_grp["correct"].mean()
        unc = len(grp) - len(decided_grp)
        print(f"    {regime:<22}: {acc:.0%}  ({decided_grp['correct'].sum():.0f}/{len(decided_grp)} decided, {unc} uncertain)")

    # Confusion matrix
    tp = len(df[(~df["ground_truth_genuine"]) & (df["predicted_status"] == "Suspicious")])
    tn = len(df[(df["ground_truth_genuine"]) & (df["predicted_status"] == "Genuine")])
    fp = len(df[(df["ground_truth_genuine"]) & (df["predicted_status"] == "Suspicious")])
    fn = len(df[(~df["ground_truth_genuine"]) & (df["predicted_status"] == "Genuine")])

    print(f"\n  Confusion matrix (Uncertain excluded):")
    print(f"    TP (correctly flagged fake):      {tp}")
    print(f"    TN (correctly cleared genuine):   {tn}")
    print(f"    FP (genuine flagged as fake):      {fp}")
    print(f"    FN (fake cleared as genuine):      {fn}")

    denom_prec = tp + fp
    denom_rec = tp + fn
    if denom_prec > 0:
        print(f"\n  Precision (suspicious detection): {tp/denom_prec:.2f}")
    if denom_rec > 0:
        print(f"  Recall    (suspicious detection): {tp/denom_rec:.2f}")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the Fake Discount Detector")
    parser.add_argument("--n", type=int, default=10, help="Products per regime (default 10)")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (default 42)")
    args = parser.parse_args()
    evaluate(n_per_regime=args.n, seed=args.seed)
