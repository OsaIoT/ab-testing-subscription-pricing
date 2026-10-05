"""Tools for looking at an experiment more than once.

- daily_looks: cumulative z-stat after each day
- calibrate_boundary: Pocock / O'Brien-Fleming critical values, found by simulation
- msprt_lambda: mixture SPRT, valid no matter how often you look
"""
import numpy as np


def daily_looks(y, t, day, n_days):
    """Cumulative diff, Welch se and z after each day (look k uses users enrolled up to day k)."""
    key = day * 2 + t
    size = n_days * 2
    n = np.bincount(key, minlength=size).reshape(n_days, 2).cumsum(0)
    s1 = np.bincount(key, weights=y, minlength=size).reshape(n_days, 2).cumsum(0)
    s2 = np.bincount(key, weights=y * y, minlength=size).reshape(n_days, 2).cumsum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        mean = s1 / n
        var = (s2 - n * mean**2) / (n - 1)
        diff = mean[:, 1] - mean[:, 0]
        se = np.sqrt(var[:, 1] / n[:, 1] + var[:, 0] / n[:, 0])
        z = diff / se
    return diff, se, np.nan_to_num(z, nan=0.0, posinf=0.0, neginf=0.0)


def simulate_sequential(y0, y1, day, n_users, n_reps, n_days, seed=0):
    """Re-run the experiment n_reps times and keep every daily look.

    Returns (diff, se, z), each (n_reps, n_days). Pass y1 = y0 for A/A tests.
    """
    rng = np.random.default_rng(seed)
    diff = np.empty((n_reps, n_days))
    se = np.empty_like(diff)
    z = np.empty_like(diff)
    for r in range(n_reps):
        idx = rng.choice(len(y0), n_users, replace=False)
        t = (rng.random(n_users) < 0.5).astype(np.int64)
        y = np.where(t == 1, y1[idx], y0[idx])
        diff[r], se[r], z[r] = daily_looks(y, t, day[idx], n_days)
    return diff, se, z


def calibrate_boundary(n_looks, shape, alpha=0.05, n_paths=200_000, seed=0):
    """Two-sided critical values for n_looks equally spaced looks.

    Under H0 the z-stat at look k behaves like S_k / sqrt(k), S_k being a sum of k
    standard normals. I simulate those random walks and take the (1 - alpha)
    quantile of the max, so the overall false positive rate is alpha.
    pocock: same bar at every look.  obf: C * sqrt(K / k), strict early, ~1.96 at the end.
    """
    rng = np.random.default_rng(seed)
    k = np.arange(1, n_looks + 1)
    z = np.abs(rng.standard_normal((n_paths, n_looks)).cumsum(axis=1)) / np.sqrt(k)
    if shape == "pocock":
        return np.full(n_looks, np.quantile(z.max(axis=1), 1 - alpha))
    if shape == "obf":
        w = np.sqrt(k / n_looks)
        return np.quantile((z * w).max(axis=1), 1 - alpha) / w
    raise ValueError(f"unknown shape {shape!r}")


def msprt_lambda(diff, se, tau2):
    """Mixture SPRT statistic with a N(0, tau2) prior on the effect.

    Lambda = sqrt(V / (V + tau2)) * exp(tau2 * diff^2 / (2 V (V + tau2))), V = se^2.
    Under H0 it's a martingale, so rejecting the first time Lambda >= 1/alpha keeps
    the error rate below alpha however often you check (Ville's inequality).
    """
    v = se**2
    with np.errstate(divide="ignore", invalid="ignore"):
        lam = np.sqrt(v / (v + tau2)) * np.exp(tau2 * diff**2 / (2 * v * (v + tau2)))
    return np.nan_to_num(lam, nan=1.0, posinf=np.inf)
