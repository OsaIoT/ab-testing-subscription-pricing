-- users per variant and per enrollment day (the SRM test itself is done in Python)
SELECT
    enroll_date,
    COUNT(*) FILTER (WHERE variant = 'treatment') AS n_treatment,
    COUNT(*) FILTER (WHERE variant = 'control')   AS n_control,
    COUNT(*)                                       AS n_total
FROM assignments
GROUP BY enroll_date
ORDER BY enroll_date
