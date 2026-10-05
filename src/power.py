"""Sample size and MDE for a two-arm test (normal approximation).

n per arm = 2 * (z_{1-alpha/2} + z_power)^2 * sigma^2 / delta^2
"""
import math

from scipy.stats import norm


def _z_sum(alpha, power):
    return norm.ppf(1 - alpha / 2) + norm.ppf(power)


def n_per_arm_mean(sigma, delta, alpha=0.05, power=0.8, variance_reduction=0.0):
    # variance_reduction is what CUPED removes (rho^2)
    var = sigma**2 * (1 - variance_reduction)
    return math.ceil(2 * _z_sum(alpha, power) ** 2 * var / delta**2)


def mde_mean(sigma, n_per_arm, alpha=0.05, power=0.8, variance_reduction=0.0):
    var = sigma**2 * (1 - variance_reduction)
    return _z_sum(alpha, power) * math.sqrt(2 * var / n_per_arm)


def n_per_arm_proportion(p_base, delta, alpha=0.05, power=0.8):
    p2 = p_base + delta
    var = p_base * (1 - p_base) + p2 * (1 - p2)
    return math.ceil(_z_sum(alpha, power) ** 2 * var / delta**2)


def duration_days(n_total, daily_eligible_users, traffic_share=1.0):
    return math.ceil(n_total / (daily_eligible_users * traffic_share))
