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
