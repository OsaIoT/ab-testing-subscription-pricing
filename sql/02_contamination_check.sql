-- should return nothing: every user assigned once, to a single variant
SELECT
    user_id,
    COUNT(*)                 AS n_assignments,
    COUNT(DISTINCT variant)  AS n_variants
FROM assignments
GROUP BY user_id
HAVING COUNT(*) > 1 OR COUNT(DISTINCT variant) > 1
