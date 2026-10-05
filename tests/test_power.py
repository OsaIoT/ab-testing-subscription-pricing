import numpy as np
from statsmodels.stats.power import tt_ind_solve_power

from src import power


def test_n_per_arm_matches_statsmodels():
    sigma, delta = 5.0, 0.1
    ref = tt_ind_solve_power(effect_size=delta / sigma, alpha=0.05, power=0.8)
    assert abs(power.n_per_arm_mean(sigma, delta) - ref) <= 2


def test_mde_is_inverse_of_sample_size():
    n = power.n_per_arm_mean(5.0, 0.1)
    assert abs(power.mde_mean(5.0, n) - 0.1) < 1e-3


def test_cuped_reduces_required_sample_size_proportionally():
    base = power.n_per_arm_mean(5.0, 0.1)
    cuped = power.n_per_arm_mean(5.0, 0.1, variance_reduction=0.27)
    assert np.isclose(cuped / base, 0.73, atol=0.01)
