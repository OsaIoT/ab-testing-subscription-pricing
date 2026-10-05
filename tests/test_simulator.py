import numpy as np

from src.simulator import SimConfig, simulate


def test_reproducible():
    a = simulate(SimConfig(n_users=5_000, seed=1))
    b = simulate(SimConfig(n_users=5_000, seed=1))
    assert a.equals(b)


def test_randomization_balanced_on_pre_covariates():
    df = simulate(SimConfig(n_users=100_000, seed=2))
    t, c = df[df.treatment == 1], df[df.treatment == 0]
    assert abs(t.sessions_pre.mean() - c.sessions_pre.mean()) < 0.15
    assert abs(t.revenue_pre_30d.mean() - c.revenue_pre_30d.mean()) < 0.15


def test_discount_is_monotone_in_conversion():
    df = simulate(SimConfig(n_users=50_000, seed=3))
    assert (df.true_ite_converted >= 0).all()


def test_ground_truth_story():
    df = simulate(SimConfig(n_users=200_000, seed=4))
    by_tier = df.groupby("tier").true_ite_revenue_30d.mean()
    assert by_tier["T1"] < 0 < by_tier["T3"]
    assert df.true_ite_revenue_60d.mean() < df.true_ite_revenue_30d.mean()


def test_observed_matches_assigned_arm():
    df = simulate(SimConfig(n_users=20_000, seed=5))
    # a payer pays at least the price of their arm
    payers_c = df[(df.treatment == 0) & (df.converted == 1)]
    assert (payers_c.revenue_30d >= 9.99 - 1e-9).all()
    payers_t = df[(df.treatment == 1) & (df.converted == 1)]
    assert (payers_t.revenue_30d >= 7.99 - 1e-9).all()
    assert np.isfinite(df.revenue_30d).all()


def test_novelty_off_by_default_and_front_loads_effect_when_on():
    base = simulate(SimConfig(n_users=100_000, seed=6))
    again = simulate(SimConfig(n_users=100_000, seed=6, novelty=0.0))
    assert base.equals(again)

    nov = simulate(SimConfig(n_users=200_000, seed=6, novelty=1.5, novelty_decay_days=5))
    early = nov[nov.enroll_day < 7].true_ite_converted.mean()
    late = nov[nov.enroll_day >= 21].true_ite_converted.mean()
    assert early > 1.4 * late


def test_cate_columns_match_realized_effects_on_average():
    df = simulate(SimConfig(n_users=300_000, seed=8))
    for metric in ["converted", "revenue_30d", "revenue_60d"]:
        realized, expected = df[f"true_ite_{metric}"], df[f"true_cate_{metric}"]
        se = realized.std() / len(df) ** 0.5
        assert abs(realized.mean() - expected.mean()) < 4 * se
    # same check inside one tier
    t3 = df[df.tier == "T3"]
    assert abs(t3.true_ite_revenue_60d.mean() - t3.true_cate_revenue_60d.mean()) < 4 * t3.true_ite_revenue_60d.std() / len(t3) ** 0.5
