-- treatment minus control with Welch standard error (p-value is computed in Python from z)
WITH s AS (
    SELECT variant, COUNT(*) AS n, AVG(revenue_30d) AS mean_rev, VAR_SAMP(revenue_30d) AS var_rev
    FROM user_metrics
    GROUP BY variant
)
SELECT
    t.n                                                           AS n_treatment,
    c.n                                                           AS n_control,
    t.mean_rev - c.mean_rev                                       AS diff,
    SQRT(t.var_rev / t.n + c.var_rev / c.n)                       AS se,
    (t.mean_rev - c.mean_rev) - 1.96 * SQRT(t.var_rev / t.n + c.var_rev / c.n) AS ci_low,
    (t.mean_rev - c.mean_rev) + 1.96 * SQRT(t.var_rev / t.n + c.var_rev / c.n) AS ci_high,
    (t.mean_rev - c.mean_rev) / SQRT(t.var_rev / t.n + c.var_rev / c.n)        AS z
FROM s t
JOIN s c ON t.variant = 'treatment' AND c.variant = 'control'
