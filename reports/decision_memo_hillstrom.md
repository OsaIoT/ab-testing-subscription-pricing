# Decision memo: e-mail campaign test (real data)

Real data: Kevin Hillstrom's public MineThatData e-mail experiment (2008). 64,000 customers who had bought something in the previous 12 months were randomized to a Men's merchandise e-mail, a Women's merchandise e-mail or no e-mail, with outcomes tracked for two weeks.

To: Marketing lead. From: Product data science.

## Recommendation

Send the Men's merchandise e-mail to all customers in this population, and don't invest in personalization based on this test.

## What the data says

| Comparison | Extra spend per customer (2 weeks) | Evidence |
|---|---|---|
| Men's e-mail vs none | +\$0.77 (95% CI +0.49 to +1.05) | clear; baseline spend is \$0.65 |
| Women's e-mail vs none | +\$0.42 (+0.17 to +0.68) | clear, smaller |
| Men's vs Women's | +\$0.35 (+0.03 to +0.66) | Holm-adjusted p = 0.03 |

* The extra revenue comes from more people buying. Conversion goes from 0.57% to 1.25% (Men's) and 0.88% (Women's), while the average order value stays around \$114-122.
* Site visits go up by 7.7 and 4.5 percentage points. That's very precise, but a visit isn't a purchase, so I only use it as supporting evidence.
* For every 1,000 customers e-mailed, the Men's e-mail brings about \$770 of extra revenue (CI \$490 to \$1,050). It's worth sending as long as it costs less than margin × \$0.77 per customer. With a 40% margin and the low end of the interval that's about \$0.19, far above what an e-mail usually costs to send.

## Why not personalize

* The "interest match" idea (Men's e-mail for past buyers of men's items, same for women's) goes in the expected direction, but the difference can't be told apart from zero.
* No exploratory segment survives the multiple-testing correction. A cross-fitted policy that picks one of the three actions for each customer doesn't beat sending the Men's e-mail to everyone (-\$0.07 per customer, CI -\$0.19 to +\$0.06), and it comes out negative on five other cross-fitting splits too.
* The test had little power to detect differences between segments (the minimum detectable difference is about twice the one for the overall comparison), because only 0.9% of customers buy and spend has a standard deviation 14 times its mean.
* One lead is worth its own test: the Women's e-mail seems to work better for new customers (omnibus heterogeneity test p = 0.014, though the single-variable test doesn't survive the correction over 12 exploratory tests).

## Risks and limits

* Two-week window, so nothing on unsubscribes, fatigue or repeat purchases. The outcome is revenue rather than profit, and the data is from 2008, covering past-year buyers of one retailer.
* CUPED and covariate adjustment gave no variance reduction (the covariates explain 0.13% of the variance), so more precision would have to come from more customers or a longer window.

## Next steps

1. Roll out the Men's e-mail and keep a small randomized holdout (for example 5% of customers) to measure long-term effects.
2. Track unsubscribe rate and 90-day revenue per customer as guardrails.
3. If personalization is still interesting, run a test large enough to detect a lift difference of about \$0.3 between segments (several times this sample), focused on the new-customer hypothesis.
