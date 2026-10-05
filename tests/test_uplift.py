import numpy as np
import pytest

from src import analysis, uplift as up


def toy_rct(n=30_000, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(n, 3))
    t = rng.integers(0, 2, n)
    tau = 1.0 * (x[:, 0] > 0)  # effect only when x0 > 0
    y = x[:, 1] + tau * t + rng.normal(size=n)
    return x, t, y, tau


def test_dr_learner_recovers_heterogeneity_on_toy_rct():
    x, t, y, tau = toy_rct()
    est = up.cross_fit(up.dr_learner, x, t, y, n_folds=3)
    assert np.corrcoef(est, tau)[0, 1] > 0.8
    assert est[x[:, 0] > 0].mean() > est[x[:, 0] <= 0].mean() + 0.5


def test_gain_curve_ends_at_ate_and_oracle_beats_random():
    x, t, y, tau = toy_rct()
    q, c = up.gain_curve(tau, t=t, y=y)
    ate = analysis.diff_in_means(y, t).estimate
    assert c[-1] == pytest.approx(ate, abs=1e-9)
    assert up.auuc(q, c, ate) > 0
    q2, c2 = up.gain_curve(np.random.default_rng(1).normal(size=len(y)), t=t, y=y)
    assert up.auuc(q, c, ate) > up.auuc(q2, c2, ate)


def test_policy_gain_of_treat_everyone_equals_difference_in_means():
    x, t, y, tau = toy_rct()
    g, se = up.policy_gain(y, t, np.ones(len(y)))
    assert g == pytest.approx(analysis.diff_in_means(y, t).estimate, abs=0.03)
    assert se > 0


def test_cross_fit_scores_every_user_out_of_fold():
    x, t, y, tau = toy_rct(6_000)
    est = up.cross_fit(up.t_learner, x, t, y, n_folds=4)
    assert est.shape == y.shape and np.isfinite(est).all()


def test_dr_policy_value_unbiased_for_three_arms():
    rng = np.random.default_rng(5)
    n = 60_000
    x = rng.normal(size=(n, 2)); arm = rng.integers(0, 3, n)
    # arm 1 helps and arm 2 hurts, but only when x0 > 0
    lift = np.array([0.0, 1.0, -0.5])[arm] * (x[:, 0] > 0)
    y = x[:, 1] + lift + rng.normal(size=n)
    mu = up.cross_fit_arm_means(x, arm, y, 3, n_folds=3)
    probs = np.full(3, 1 / 3)
    best = np.where(x[:, 0] > 0, 1, 0)
    v_best, se = up.dr_policy_value(mu, arm, y, best, probs)
    v_none, _ = up.dr_policy_value(mu, arm, y, np.zeros(n, int), probs)
    assert v_best - v_none == pytest.approx(0.5, abs=4 * se + 0.05)  # P(x0 > 0) * 1.0
    helped = x[:, 0] > 0  # elsewhere all arms are equal so argmax is arbitrary
    assert (mu.argmax(1)[helped] == 1).mean() > 0.8
