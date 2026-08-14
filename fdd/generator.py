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
