"""Helpers for analysing a randomized experiment."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import chisquare, norm
from statsmodels.stats.multitest import multipletests


@dataclass
class Effect:
    estimate: float
    se: float
    ci_low: float
    ci_high: float
    p_value: float
    n_treat: int
    n_control: int

    def __str__(self):
        return (f"{self.estimate:+.4f}  95% CI [{self.ci_low:+.4f}, {self.ci_high:+.4f}]  "
                f"se={self.se:.4f}  p={self.p_value:.3f}")


def srm_check(n_treat, n_control, expected_share_treat=0.5):
    """Chi-square p-value for sample ratio mismatch. I treat p < 0.001 as a broken experiment."""
    total = n_treat + n_control
    expected = [total * expected_share_treat, total * (1 - expected_share_treat)]
    return float(chisquare([n_treat, n_control], f_exp=expected).pvalue)


def srm_check_multi(counts, expected_shares=None):
    """Same as srm_check but for any number of arms (equal split by default)."""
    counts = np.asarray(counts, dtype=float)
    if expected_shares is None:
        shares = np.full(len(counts), 1 / len(counts))
    else:
        shares = np.asarray(expected_shares, float)
    return float(chisquare(counts, f_exp=counts.sum() * shares).pvalue)


def standardized_mean_diff(x, t):
    # (mean_T - mean_C) / pooled sd, anything under 0.1 is usually considered balanced
    xt, xc = x[t == 1], x[t == 0]
    pooled = np.sqrt((xt.var(ddof=1) + xc.var(ddof=1)) / 2)
    return float((xt.mean() - xc.mean()) / pooled)


def diff_in_means(y, t, alpha=0.05):
    """Treatment minus control, Welch standard error, normal approximation."""
    yt, yc = y[t == 1], y[t == 0]
    est = yt.mean() - yc.mean()
    se = np.sqrt(yt.var(ddof=1) / len(yt) + yc.var(ddof=1) / len(yc))
    z = norm.ppf(1 - alpha / 2)
    p = 2 * (1 - norm.cdf(abs(est / se)))
    return Effect(est, se, est - z * se, est + z * se, p, len(yt), len(yc))


def bootstrap_diff(y, t, n_boot=1000, alpha=0.05, seed=0):
    """Percentile bootstrap CI for the difference in means."""
    rng = np.random.default_rng(seed)
    yt, yc = y[t == 1], y[t == 0]
    diffs = np.empty(n_boot)
    for b in range(n_boot):
        diffs[b] = rng.choice(yt, len(yt)).mean() - rng.choice(yc, len(yc)).mean()
    return tuple(np.quantile(diffs, [alpha / 2, 1 - alpha / 2]))


def cuped_adjust(y, x):
    """CUPED: y - theta * (x - mean(x)) with theta = cov(y, x) / var(x).

    x has to be measured before the experiment starts, otherwise the treatment
    could move it and the estimate is no longer unbiased.
    """
    theta = np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)
    return y - theta * (x - x.mean()), float(theta)


def cuped_effect(y, x, t):
    """Effect on the CUPED-adjusted outcome plus the share of variance removed."""
    y_adj, _ = cuped_adjust(y, x)
    return diff_in_means(y_adj, t), 1 - y_adj.var(ddof=1) / y.var(ddof=1)


def subgroup_effects(df, by, outcome, treat="treatment", truth=None):
    """Effect inside each level of `by`, with Holm-adjusted p-values across the levels."""
    rows = []
    for level, g in df.groupby(by):
        e = diff_in_means(g[outcome].to_numpy(), g[treat].to_numpy())
        row = {by: level, "n": len(g), "estimate": e.estimate, "ci_low": e.ci_low,
               "ci_high": e.ci_high, "p_value": e.p_value}
        if truth:
            row["true_effect"] = g[truth].mean()
        rows.append(row)
    out = pd.DataFrame(rows)
    out["p_holm"] = multipletests(out["p_value"], method="holm")[1]
    return out


# The two functions below only work on simulated data (they need the true effects).

def potential_outcomes(df, outcome):
    """Rebuild (Y(0), Y(1)) for every user from the observed value and the true ITE."""
    ite = df[f"true_ite_{outcome}"].to_numpy()
    y0 = df[outcome].to_numpy() - df["treatment"].to_numpy() * ite
    return y0, y0 + ite


def monte_carlo(df, outcome, covariate, n_users, n_reps, true_effect_override=None, seed=0):
    """Re-run the experiment many times on random subsamples with a new coin flip each time.

    With true_effect_override=0 every run is an A/A test.
    """
    rng = np.random.default_rng(seed)
    y0, y1 = potential_outcomes(df, outcome)
    x_all = df[covariate].to_numpy()
    if true_effect_override is not None:
        y1 = y0 + true_effect_override
    target = (y1 - y0).mean()
    rows = []
    for _ in range(n_reps):
        idx = rng.choice(len(df), n_users, replace=False)
        t = (rng.random(n_users) < 0.5).astype(int)
        y = np.where(t == 1, y1[idx], y0[idx])
        naive = diff_in_means(y, t)
        cup, vr = cuped_effect(y, x_all[idx], t)
        rows.append({
            "naive_est": naive.estimate, "naive_se": naive.se,
            "naive_covers": naive.ci_low <= target <= naive.ci_high, "naive_p": naive.p_value,
            "cuped_est": cup.estimate, "cuped_se": cup.se,
            "cuped_covers": cup.ci_low <= target <= cup.ci_high, "cuped_p": cup.p_value,
            "var_reduction": vr,
        })
    res = pd.DataFrame(rows)
    res.attrs["target"] = target
    return res
