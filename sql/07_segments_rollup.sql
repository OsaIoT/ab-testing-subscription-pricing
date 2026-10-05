-- effect by tier plus the overall row (ROLLUP adds the total with tier = NULL)
WITH s AS (
    SELECT COALESCE(tier, 'ALL') AS segment, variant,
           COUNT(*) AS n, AVG(revenue_30d) AS m, VAR_SAMP(revenue_30d) AS v
    FROM user_metrics
    GROUP BY ROLLUP (tier), variant
)
SELECT
    t.segment,
    t.n + c.n                              AS n_users,
    t.m - c.m                              AS diff,
    SQRT(t.v / t.n + c.v / c.n)            AS se,
    (t.m - c.m) / SQRT(t.v / t.n + c.v / c.n) AS z
FROM s t
JOIN s c ON t.segment = c.segment AND t.variant = 'treatment' AND c.variant = 'control'
ORDER BY CASE WHEN t.segment = 'ALL' THEN 0 ELSE 1 END, t.segment
