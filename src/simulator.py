"""
Toy simulator for a paywall pricing test in a freemium subscription app.

Users who hit the paywall see either the normal price (9.99/month) or a 20%
discount (7.99). Since it's a simulation I generate both potential outcomes for
every user, so I know the true effect and can check if the estimators find it.

Things I put in on purpose:
- price sensitivity depends on country tier and engagement (the discount loses
  money in T1, is about break-even in T2 and wins in T3)
- people who convert only because of the discount churn more in month 2
- past in-app spend predicts future spend, so CUPED has something to work with
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


@dataclass
class SimConfig:
    n_users: int = 200_000
    n_days: int = 28              # enrollment window
    p_treat: float = 0.5
    price_control: float = 9.99
    price_variant: float = 7.99

    # conversion model on the log-odds scale, intercept gives ~5% baseline
    intercept: float = -3.3
    b_engagement: float = 0.45
    b_spender: float = 0.35
    b_ios: float = 0.25
    tier_shift: dict = field(default_factory=lambda: {"T1": 0.30, "T2": 0.0, "T3": -0.40})

    # price sensitivity = change in log-odds per unit drop in log(price).
    # Around 1.0 a 20% discount is roughly revenue neutral on subscriptions.
    beta_tier: dict = field(default_factory=lambda: {"T1": 0.4, "T2": 1.0, "T3": 2.2})
    beta_engagement_decay: float = 0.25    # engaged users care less about price
    # novelty: sensitivity multiplied by 1 + novelty * exp(-enroll_day / decay). Off by default.
    novelty: float = 0.0
    novelty_decay_days: float = 5.0

    # month-2 retention of payers (discount-only converters retain worse)
    retention_intercept: float = 0.3
    retention_engagement: float = 0.5
    retention_marginal_penalty: float = -0.6

    # in-app purchases: Poisson number of purchases, lognormal amounts
    iap_intercept: float = -4.4
    iap_engagement: float = 0.6
    iap_spender: float = 1.4
    iap_amount_mu: float = 1.2
    iap_amount_spender: float = 0.5
    iap_amount_sigma: float = 0.8

    seed: int = 42


def simulate(cfg=None):
    """One row per enrolled user.

    The observed columns are what you'd have in a real experiment. Columns starting
    with `true_` are only known because this is a simulation:
    `true_ite_*` is the realized individual effect, `true_cate_*` the expected
    effect given the user's (hidden) traits.
    """
    cfg = cfg or SimConfig()
    rng = np.random.default_rng(cfg.seed)
    n = cfg.n_users

    tier = rng.choice(["T1", "T2", "T3"], size=n, p=[0.35, 0.40, 0.25])
    platform = rng.choice(["ios", "android"], size=n, p=[0.45, 0.55])
    z = rng.normal(size=n)    # hidden engagement
    w = rng.normal(size=n)    # hidden "likes to spend" trait, stable over time
    sessions_pre = rng.poisson(np.exp(2.0 + 0.6 * z))
    tenure_days = 1 + rng.exponential(120, size=n).astype(int)
    enroll_day = rng.integers(0, cfg.n_days, size=n)
    treatment = rng.random(n) < cfg.p_treat

    # spend in the 30 days before the test, driven by the same traits
    revenue_pre = _iap_revenue(rng, z, w, cfg)

    # conversion probability under both prices
    tier_shift = pd.Series(tier).map(cfg.tier_shift).to_numpy()
    base_logit = (
        cfg.intercept
        + cfg.b_engagement * z
        + cfg.b_spender * w
        + cfg.b_ios * (platform == "ios")
        + tier_shift
    )
    beta = pd.Series(tier).map(cfg.beta_tier).to_numpy() * np.exp(-cfg.beta_engagement_decay * z)
    beta = beta * (1 + cfg.novelty * np.exp(-enroll_day / cfg.novelty_decay_days))
    log_price_ratio = np.log(cfg.price_variant / cfg.price_control)   # < 0
    p_control = _sigmoid(base_logit)
    p_variant = _sigmoid(base_logit - beta * log_price_ratio)

    # same uniform draw for both prices, so the discount can only add converters
    u_conv = rng.random(n)
    conv_c = u_conv < p_control
    conv_v = u_conv < p_variant
    marginal = conv_v & ~conv_c    # would not have paid at full price

    ret_logit = cfg.retention_intercept + cfg.retention_engagement * z
    u_ret = rng.random(n)
    ret_c = u_ret < _sigmoid(ret_logit)
    ret_v = u_ret < _sigmoid(ret_logit + cfg.retention_marginal_penalty * marginal)

    # expected effects given the hidden traits (no coin flips), used to grade the uplift models
    r_c, r_m = _sigmoid(ret_logit), _sigmoid(ret_logit + cfg.retention_marginal_penalty)
    cate_30 = cfg.price_variant * p_variant - cfg.price_control * p_control
    cate_60 = cate_30 + (cfg.price_variant * (p_control * r_c + (p_variant - p_control) * r_m)
                         - cfg.price_control * p_control * r_c)

    # in-app spend after enrollment, same in both arms
    iap_post = _iap_revenue(rng, z, w, cfg)

    rev30_c = cfg.price_control * conv_c + iap_post
    rev30_v = cfg.price_variant * conv_v + iap_post
    rev60_c = rev30_c + cfg.price_control * (conv_c & ret_c)
    rev60_v = rev30_v + cfg.price_variant * (conv_v & ret_v)

    def observed(ctrl, var):
        return np.where(treatment, var, ctrl)

    converted = observed(conv_c, conv_v)
    df = pd.DataFrame({
        "user_id": np.arange(n),
        "enroll_day": enroll_day,
        "treatment": treatment.astype(int),
        "tier": tier,
        "platform": platform,
        "sessions_pre": sessions_pre,
        "tenure_days": tenure_days,
        "revenue_pre_30d": revenue_pre,
        "converted": converted.astype(int),
        "retained_m2": (converted & observed(ret_c, ret_v)).astype(int),
        "revenue_30d": observed(rev30_c, rev30_v),
        "revenue_60d": observed(rev60_c, rev60_v),
        "true_ite_converted": conv_v.astype(int) - conv_c.astype(int),
        "true_ite_revenue_30d": rev30_v - rev30_c,
        "true_ite_revenue_60d": rev60_v - rev60_c,
        "true_cate_converted": p_variant - p_control,
        "true_cate_revenue_30d": cate_30,
        "true_cate_revenue_60d": cate_60,
    })
    return df.sort_values(["enroll_day", "user_id"]).reset_index(drop=True)


def _iap_revenue(rng, z, w, cfg):
    # 30 days of in-app purchases: Poisson count, each purchase lognormal
    rate = np.exp(cfg.iap_intercept + cfg.iap_engagement * z + cfg.iap_spender * w)
    counts = rng.poisson(rate)
    mu = cfg.iap_amount_mu + cfg.iap_amount_spender * w
    owner = np.repeat(np.arange(len(z)), counts)
    amounts = rng.lognormal(mu[owner], cfg.iap_amount_sigma)
    return np.bincount(owner, weights=amounts, minlength=len(z))


if __name__ == "__main__":
    df = simulate()
    print(df.head())
    print(df.describe().T)
