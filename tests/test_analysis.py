import numpy as np
import pytest

from src import analysis
from src.simulator import SimConfig, simulate


@pytest.fixture(scope="module")
def df():
    return simulate(SimConfig(n_users=60_000, seed=11))


def test_srm_flags_broken_split_and_passes_clean_one():
    assert analysis.srm_check(50_300, 49_700) > 0.001
    assert analysis.srm_check(51_500, 48_500) < 0.001  # 3% off with n=100k is a bug


def test_diff_in_means_recovers_known_shift():
    rng = np.random.default_rng(0)
    t = rng.integers(0, 2, 50_000)
    y = rng.normal(size=50_000) + 0.2 * t
    e = analysis.diff_in_means(y, t)
    assert e.ci_low < 0.2 < e.ci_high


def test_cuped_variance_reduction_matches_rho_squared(df):
    y, x = df.revenue_30d.to_numpy(), df.revenue_pre_30d.to_numpy()
    _, vr = analysis.cuped_effect(y, x, df.treatment.to_numpy())
    rho2 = np.corrcoef(y, x)[0, 1] ** 2
    assert vr == pytest.approx(rho2, abs=0.01)


def test_potential_outcomes_consistent_with_observed(df):
    y0, y1 = analysis.potential_outcomes(df, "revenue_30d")
    observed = np.where(df.treatment == 1, y1, y0)
    assert np.allclose(observed, df.revenue_30d)


def test_aa_test_false_positive_rate_near_alpha(df):
    res = analysis.monte_carlo(df, "revenue_30d", "revenue_pre_30d", n_users=10_000,
                               n_reps=400, true_effect_override=0.0, seed=1)
    assert 0.02 < (res.naive_p < 0.05).mean() < 0.09
    assert 0.02 < (res.cuped_p < 0.05).mean() < 0.09


def test_srm_multi_arm():
    assert analysis.srm_check_multi([21387, 21307, 21306]) > 0.5
    assert analysis.srm_check_multi([24000, 20000, 20000]) < 0.001
