-- Hillstrom funnel by arm. MAX(...) FILTER (...) OVER () puts the control value on every row, no self join needed
WITH f AS (
    SELECT segment,
           COUNT(*)        AS customers,
           SUM(visit)      AS visits,
           SUM(conversion) AS buyers,
           AVG(visit)      AS visit_rate,
           AVG(conversion) AS conversion_rate,
           AVG(spend)      AS spend_per_customer
    FROM hillstrom
    GROUP BY segment
)
SELECT segment, customers, visit_rate, conversion_rate,
       buyers * 1.0 / NULLIF(visits, 0)                        AS buyers_per_visitor,
       spend_per_customer,
       spend_per_customer - MAX(spend_per_customer) FILTER (WHERE segment = 'No E-Mail') OVER () AS lift_vs_control
FROM f
ORDER BY spend_per_customer DESC
