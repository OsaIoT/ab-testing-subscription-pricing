-- lift of each e-mail over no e-mail, by channel
SELECT
    channel,
    COUNT(*)                                                                    AS customers,
    AVG(spend) FILTER (WHERE segment = 'Mens E-Mail')
      - AVG(spend) FILTER (WHERE segment = 'No E-Mail')                          AS mens_lift,
    AVG(spend) FILTER (WHERE segment = 'Womens E-Mail')
      - AVG(spend) FILTER (WHERE segment = 'No E-Mail')                          AS womens_lift
FROM hillstrom
GROUP BY channel
ORDER BY channel
