import numpy as np
import pytest

from src import analysis, sequential as seq


def test_calibrated_boundaries_match_published_tables():
    # published values for K=4, two-sided alpha=0.05 (Jennison & Turnbull)
    pocock = seq.calibrate_boundary(4, "pocock", n_paths=400_000, seed=1)
    obf = seq.calibrate_boundary(4, "obf", n_paths=400_000, seed=1)
    assert pocock[0] == pytest.approx(2.361, abs=0.03)
    assert obf[-1] == pytest.approx(2.024, abs=0.03)
    assert obf[0] > obf[-1]


def test_last_look_equals_standard_welch_z():
    rng = np.random.default_rng(0)
    n, days = 20_000, 10
    day = rng.integers(0, days, n); t = rng.integers(0, 2, n); y = rng.normal(size=n) + 0.1 * t
    diff, se, z = seq.daily_looks(y, t, day, days)
    ref = analysis.diff_in_means(y, t)
    assert diff[-1] == pytest.approx(ref.estimate) and se[-1] == pytest.approx(ref.se)


def test_msprt_keeps_type1_error_under_continuous_monitoring():
    rng = np.random.default_rng(3)
    n, days, reps = 20_000, 28, 600
    day = np.sort(rng.integers(0, days, n))
    rejected = 0
    for _ in range(reps):  # A/A
        t = rng.integers(0, 2, n); y = rng.normal(size=n)
        diff, se, _ = seq.daily_looks(y, t, day, days)
        rejected += (seq.msprt_lambda(diff, se, tau2=0.05**2) >= 20).any()
    assert rejected / reps < 0.08  # 5% plus some simulation noise


def test_naive_peeking_inflates_false_positives():
    rng = np.random.default_rng(4)
    n, days, reps = 20_000, 28, 600
    day = np.sort(rng.integers(0, days, n))
    rejected = 0
    for _ in range(reps):
        t = rng.integers(0, 2, n); y = rng.normal(size=n)
        _, _, z = seq.daily_looks(y, t, day, days)
        rejected += (np.abs(z) > 1.96).any()
    assert rejected / reps > 0.15
