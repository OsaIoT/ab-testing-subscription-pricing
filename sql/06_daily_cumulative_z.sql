-- cumulative z after each day, from running sums of n, sum(y) and sum(y^2)
WITH daily AS (
    SELECT enroll_date, variant,
           COUNT(*) AS n, SUM(revenue_30d) AS s1, SUM(revenue_30d * revenue_30d) AS s2
    FROM user_metrics
    GROUP BY enroll_date, variant
),
cum AS (
    SELECT enroll_date, variant,
           SUM(n)  OVER w AS n,
           SUM(s1) OVER w AS s1,
           SUM(s2) OVER w AS s2
    FROM daily
    WINDOW w AS (PARTITION BY variant ORDER BY enroll_date)
),
stats AS (
    SELECT enroll_date, variant, n,
           s1 / n                                   AS mean,
           (s2 - n * (s1 / n) * (s1 / n)) / (n - 1) AS var
    FROM cum
)
SELECT
    t.enroll_date,
    t.n AS n_treatment,
    c.n AS n_control,
    t.mean - c.mean                                                  AS diff,
    SQRT(t.var / t.n + c.var / c.n)                                  AS se,
    (t.mean - c.mean) / SQRT(t.var / t.n + c.var / c.n)              AS z
FROM stats t
JOIN stats c ON t.enroll_date = c.enroll_date AND t.variant = 'treatment' AND c.variant = 'control'
ORDER BY t.enroll_date
