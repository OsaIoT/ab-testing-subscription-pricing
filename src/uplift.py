"""Uplift / CATE learners for randomized data, plus cross-fitting and policy evaluation.

All learners return tau_hat(x), an estimate of E[Y(1) - Y(0) | X = x]:
- S-learner: one model, treatment as a feature
- T-learner: one model per arm, take the difference
- DR-learner: regress the doubly robust pseudo-outcome on x
- structural: DR-learner on conversion (0/1, much less noisy) and then price algebra for revenue
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import KFold

FEATURES = ["sessions_pre", "tenure_days", "revenue_pre_30d", "is_ios", "tier_T1", "tier_T2", "tier_T3"]


def make_features(df):
    # only things known before enrollment
    return pd.DataFrame({
        "sessions_pre": df.sessions_pre, "tenure_days": df.tenure_days,
        "revenue_pre_30d": df.revenue_pre_30d, "is_ios": (df.platform == "ios").astype(int),
        "tier_T1": (df.tier == "T1").astype(int), "tier_T2": (df.tier == "T2").astype(int),
        "tier_T3": (df.tier == "T3").astype(int),
    })[FEATURES].to_numpy(float)


# Hyperparameters picked up front: the signal is weak so I keep the trees shallow and
# regularized. I did not tune them against the true effects (that would be cheating).
def _reg(depth=3, leaf=200, iters=200, lr=0.05, seed=0):
    return HistGradientBoostingRegressor(max_depth=depth, min_samples_leaf=leaf, max_iter=iters,
                                         learning_rate=lr, l2_regularization=1.0, random_state=seed)


def _clf(depth=3, leaf=200, iters=200, lr=0.05, seed=0):
    return HistGradientBoostingClassifier(max_depth=depth, min_samples_leaf=leaf, max_iter=iters,
                                          learning_rate=lr, l2_regularization=1.0, random_state=seed)


def s_learner(Xtr, ttr, ytr, Xte, **_):
    m = _reg().fit(np.column_stack([Xtr, ttr]), ytr)
    treated = m.predict(np.column_stack([Xte, np.ones(len(Xte))]))
    control = m.predict(np.column_stack([Xte, np.zeros(len(Xte))]))
    return treated - control


def t_learner(Xtr, ttr, ytr, Xte, **_):
    m1 = _reg().fit(Xtr[ttr == 1], ytr[ttr == 1])
    m0 = _reg().fit(Xtr[ttr == 0], ytr[ttr == 0])
    return m1.predict(Xte) - m0.predict(Xte)


def dr_learner(Xtr, ttr, ytr, Xte, binary=False, e=0.5, n_folds=2, final_leaf=5000, seed=0, **_):
    """DR-learner.

    psi = mu1 - mu0 + T (y - mu1) / e - (1 - T) (y - mu0) / (1 - e), with mu fitted on the
    other fold. Since e is known (it's an RCT), E[psi | x] = tau(x) even if mu is bad.
    psi is very noisy though, so the final model is small.
    """
    psi = np.empty(len(ytr))
    for fit_idx, pred_idx in KFold(n_folds, shuffle=True, random_state=seed).split(Xtr):
        mu = {}
        for arm in (0, 1):
            rows = fit_idx[ttr[fit_idx] == arm]
            model = _clf() if binary else _reg()
            model.fit(Xtr[rows], ytr[rows])
            if binary:
                mu[arm] = model.predict_proba(Xtr[pred_idx])[:, 1]
            else:
                mu[arm] = model.predict(Xtr[pred_idx])
        t, y = ttr[pred_idx], ytr[pred_idx]
        psi[pred_idx] = mu[1] - mu[0] + t * (y - mu[1]) / e - (1 - t) * (y - mu[0]) / (1 - e)
    return _reg(depth=2, leaf=final_leaf, iters=100).fit(Xtr, psi).predict(Xte)


def structural_learner(Xtr, ttr, ytr, Xte, conv=None, price_control=9.99, price_variant=7.99, **kw):
    """Revenue CATE built from the conversion CATE.

    Subscription revenue is price * converted, so
        tau_rev(x) = p_v * tau_conv(x) + (p_v - p_c) * q_c(x)
    where q_c is the baseline conversion probability. Assumes the price doesn't change
    in-app spending (I check this in notebook 03) and that prices are known.
    """
    tau_conv = dr_learner(Xtr, ttr, conv, Xte, binary=True, **kw)
    q_c = _clf().fit(Xtr[ttr == 0], conv[ttr == 0]).predict_proba(Xte)[:, 1]
    return price_variant * tau_conv + (price_variant - price_control) * q_c


def cross_fit(learner, X, t, y, n_folds=5, seed=0, **kw):
    """Out-of-fold predictions: each user is scored by a model that didn't train on them."""
    out = np.empty(len(y))
    for tr, te in KFold(n_folds, shuffle=True, random_state=seed).split(X):
        # per-user arrays passed through kw (e.g. conv) have to be split too
        extra = {k: (v[tr] if isinstance(v, np.ndarray) and len(v) == len(y) else v) for k, v in kw.items()}
        out[te] = learner(X[tr], t[tr], y[tr], X[te], **extra)
    return out


def gain_curve(score, t=None, y=None, ite=None, n_points=100):
    """Gain per user (of the whole population) when treating the top-q share by score.

    With y and t it uses the experiment data (diff in means in the top-q group).
    With ite it uses the true effects, simulation only.
    """
    order = np.argsort(-score, kind="stable")
    n = len(score)
    idx = np.unique((np.linspace(0.01, 1.0, n_points) * n).astype(int)) - 1
    q = (idx + 1) / n
    if ite is not None:
        return q, np.cumsum(ite[order])[idx] / n
    ys, ts = y[order], t[order]
    nt, nc = np.cumsum(ts), np.cumsum(1 - ts)
    yt, yc = np.cumsum(ys * ts), np.cumsum(ys * (1 - ts))
    return q, (yt[idx] / nt[idx] - yc[idx] / nc[idx]) * q


def auuc(q, curve, ate):
    # area between the gain curve and random targeting (the line q * ATE)
    return float(np.trapezoid(curve - q * ate, q))


def policy_gain(y, t, policy, e=0.5):
    """IPW estimate of E[policy(x) * (Y(1) - Y(0))] and its standard error."""
    psi = policy * (t * y / e - (1 - t) * y / (1 - e))
    return float(psi.mean()), float(psi.std(ddof=1) / np.sqrt(len(psi)))


# Policies with more than two actions (used for the e-mail data: none / men's / women's)

def cross_fit_arm_means(X, arm, y, n_arms, n_folds=5, seed=0, **reg_kw):
    """Out-of-fold mu_a(x) = E[Y | x, arm a] for each arm, shape (n, n_arms)."""
    mu = np.zeros((len(y), n_arms))
    for tr, te in KFold(n_folds, shuffle=True, random_state=seed).split(X):
        for a in range(n_arms):
            rows = tr[arm[tr] == a]
            mu[te, a] = _reg(**reg_kw).fit(X[rows], y[rows]).predict(X[te])
    return mu


def dr_policy_scores(mu, arm, y, policy, probs):
    """Doubly robust score per user: mu_pi + 1[arm == pi] * (y - mu_pi) / P(arm == pi).

    Its mean is unbiased for the policy value as long as mu is out-of-fold and the
    assignment probabilities are known.
    """
    idx = np.arange(len(y))
    m = mu[idx, policy]
    return m + (arm == policy) * (y - m) / np.asarray(probs)[policy]


def dr_policy_value(mu, arm, y, policy, probs):
    s = dr_policy_scores(mu, arm, y, policy, probs)
    return float(s.mean()), float(s.std(ddof=1) / np.sqrt(len(s)))
