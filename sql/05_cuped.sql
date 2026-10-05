-- CUPED: theta = cov(y, x) / var(x) on all users, then the usual comparison on the adjusted y
WITH th AS (
    SELECT COVAR_SAMP(revenue_30d, revenue_pre_30d) / VAR_SAMP(revenue_pre_30d) AS theta,
           AVG(revenue_pre_30d)                                                  AS x_bar
    FROM user_metrics
),
adj AS (
    SELECT m.variant, m.revenue_30d - th.theta * (m.revenue_pre_30d - th.x_bar) AS y_adj
    FROM user_metrics m CROSS JOIN th
),
s AS (
    SELECT variant, COUNT(*) AS n, AVG(y_adj) AS mean_y, VAR_SAMP(y_adj) AS var_y
    FROM adj
    GROUP BY variant
)
SELECT
    (SELECT theta FROM th)                                          AS theta,
    1 - (SELECT VAR_SAMP(y_adj) FROM adj)
          / (SELECT VAR_SAMP(revenue_30d) FROM user_metrics)        AS variance_reduction,
    t.mean_y - c.mean_y                                             AS diff_cuped,
    SQRT(t.var_y / t.n + c.var_y / c.n)                             AS se_cuped,
    (t.mean_y - c.mean_y) / SQRT(t.var_y / t.n + c.var_y / c.n)     AS z_cuped
FROM s t
JOIN s c ON t.variant = 'treatment' AND c.variant = 'control'
