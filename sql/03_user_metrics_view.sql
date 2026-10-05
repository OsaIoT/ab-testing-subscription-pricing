-- one row per exposed user with all the metrics
-- assignments on the left + LEFT JOIN, so users who never paid stay in with 0.
-- windows start at each user's own enroll_date, and the pre-period window ends before it
CREATE OR REPLACE VIEW user_metrics AS
SELECT
    a.user_id,
    a.variant,
    a.enroll_date,
    u.tier,
    u.platform,
    COALESCE(MAX(CASE WHEN p.kind = 'subscription'
                       AND p.purchase_ts >= a.enroll_date
                       AND p.purchase_ts <  a.enroll_date + INTERVAL 14 DAY THEN 1 END), 0) AS converted,
    COALESCE(MAX(CASE WHEN p.kind = 'subscription_renewal'
                       AND p.purchase_ts <  a.enroll_date + INTERVAL 60 DAY THEN 1 END), 0) AS retained_m2,
    COALESCE(SUM(CASE WHEN p.purchase_ts >= a.enroll_date
                       AND p.purchase_ts <  a.enroll_date + INTERVAL 30 DAY THEN p.amount END), 0) AS revenue_30d,
    COALESCE(SUM(CASE WHEN p.purchase_ts >= a.enroll_date
                       AND p.purchase_ts <  a.enroll_date + INTERVAL 60 DAY THEN p.amount END), 0) AS revenue_60d,
    COALESCE(SUM(CASE WHEN p.purchase_ts >= a.enroll_date - INTERVAL 30 DAY
                       AND p.purchase_ts <  a.enroll_date THEN p.amount END), 0)                  AS revenue_pre_30d
FROM assignments a
JOIN users u USING (user_id)
LEFT JOIN purchases p ON p.user_id = a.user_id
GROUP BY a.user_id, a.variant, a.enroll_date, u.tier, u.platform
