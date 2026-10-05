-- common bug: INNER JOIN to purchases keeps only buyers, so the average is over buyers
-- and the denominator is different in each arm
WITH wrong AS (
    SELECT variant, AVG(rev) AS arpu_inner_join
    FROM (
        SELECT a.user_id, a.variant, SUM(p.amount) AS rev
        FROM assignments a
        JOIN purchases p
          ON p.user_id = a.user_id
         AND p.purchase_ts >= a.enroll_date
         AND p.purchase_ts <  a.enroll_date + INTERVAL 30 DAY
        GROUP BY a.user_id, a.variant
    )
    GROUP BY variant
),
correct AS (
    SELECT variant, AVG(revenue_30d) AS arpu_all_exposed_users, COUNT(*) AS exposed_users
    FROM user_metrics
    GROUP BY variant
)
SELECT c.variant, c.exposed_users, c.arpu_all_exposed_users, w.arpu_inner_join
FROM correct c JOIN wrong w USING (variant)
ORDER BY c.variant
