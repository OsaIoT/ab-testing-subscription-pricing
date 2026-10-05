# Decision memo: 20% lower subscription price (from 9.99 to 7.99 € per month)

Simulated data: the experiment, its results and the "company" are a simulation I built for this project. The memo shows how I would write up a real result.

To: Product lead, Growth. From: Product data science. Experiment: 200,000 users who hit the paywall, randomized 50/50 over 28 days.

## Recommendation

1. Don't roll out the discount to everyone. It doesn't raise revenue on average and it loses money in the largest segment.
2. Keep the current price in T1 (rich countries, 35% of users) and in T2.
3. Launch the discount in T3 (price-sensitive users, 25% of the total) in stages with a 20% holdback and a sequential stopping rule. The alternative, a revenue-based confirmation test, would take about 10 months.

## What the data says

| | Effect of the discount on 30-day revenue per user | |
|---|---|---|
| All users | -0.019 € (95% CI -0.058 to +0.021) | can't be told apart from zero |
| T1 | -0.105 € (-0.173 to -0.038), Holm p = 0.007 | clear loss |
| T2 | -0.001 € (-0.062 to +0.060) | neutral |
| T3 | +0.074 € (-0.007 to +0.155), Holm p = 0.15 | likely gain, not confirmed on total revenue |

* Conversion is up by 1.0 percentage point (p < 0.001), but each payer pays 20% less. Reading conversion alone, we would have shipped.
* It gets worse over time. At 60 days the overall effect is -0.050 € (CI -0.097 to -0.004), because the payers won by the discount churn more: month-2 retention among payers is 58.6% against 63.0% in control.
* The case for T3 gets stronger if in-app purchases are left out. They show no effect of the price (+0.005 €, p = 0.80), so under that assumption subscription revenue alone is a valid and much less noisy measure. On that basis, giving the discount only in T3 gains +0.017 € per eligible user (95% CI +0.009 to +0.024), about +€16,500 per million eligible users per 30 days (CI €8,700 to €24,300). Shipping to everyone comes out at -€16,700 per million users (CI -€34,800 to +€1,400).
* A targeting model (conversion uplift plus price algebra, cross-fitted) gives a similar gain (+€18,400 per million, CI €6,800 to €30,000) and doesn't beat the tier rule, so I'd go with the tier rule because it's simpler.

## Risks and assumptions

* Winner's curse: T3 was chosen because it looked best, so its real gain is probably below +0.074 €. The holdback works as the confirmatory test.
* The assumption that in-app purchases don't react to the price rests on a null result and isn't proven.
* Only 60 days are observed. Lifetime value and refunds after that are unknown, and so are cannibalization of annual plans, price anchoring and fairness perceptions (T3 users comparing prices).
* The segments are country tiers, so legal and pricing-policy constraints have to be checked before charging different prices.

## Next steps

1. Launch the T3 price to 80% of T3 traffic with a 20% holdback. Primary metric: subscription revenue per user. Guardrails: 60- and 90-day retention and refunds. O'Brien-Fleming boundaries with weekly looks.
2. Keep the current price in T1 and T2, and re-test T2 only with a larger sample, since its effect is centred on zero.
3. Add a 90-day readout to the T3 launch before extending the policy to other markets.

*Check against the simulation: since the simulator knows the truth, I can verify this recommendation. Giving the discount only in T3 truly gains €19,800 per million users per 30 days, and shipping to everyone truly loses €14,500, in line with the estimates above. See notebooks 01 and 03.*
