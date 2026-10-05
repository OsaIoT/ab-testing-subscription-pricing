-- month-2 retention by weekly cohort, two ways:
-- among payers (not comparable across arms since the discount changes who pays)
-- and per exposed user
SELECT
    DATE_TRUNC('week', enroll_date)                              AS cohort_week,
    variant,
    COUNT(*)                                                     AS exposed_users,
    SUM(converted)                                               AS payers,
    SUM(retained_m2)                                             AS retained_payers,
    SUM(retained_m2) * 1.0 / NULLIF(SUM(converted), 0)           AS retention_among_payers,
    SUM(retained_m2) * 1.0 / COUNT(*)                            AS retained_per_exposed_user
FROM user_metrics
GROUP BY 1, 2
ORDER BY 1, 2
