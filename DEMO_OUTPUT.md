# RouteFlow — Demo Output

Captured output of `python3 scripts/demo.py`, showing the Bayesian learning algorithm
in action across 5 steps. Run against a fresh database, then against 600 seeded transactions.

---

## Step 1 — Recommendations with NO historical data (pure priors)

With zero transactions in the database, scores equal the hardcoded priors from `app/config.py`.

**Brazil** (`BRL 150.00`)
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | pix | 0.8500 | 0.8500 | 0 |
| 2 | boleto | 0.6500 | 0.6500 | 0 |
| 3 | credit_card | 0.1500 | 0.1500 | 0 |

**Mexico** (`MXN 500.00`)
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | oxxo | 0.7200 | 0.7200 | 0 |
| 2 | spei | 0.5780 | 0.6800 | 0 |
| 3 | credit_card | 0.2000 | 0.2000 | 0 |

> Note: SPEI score (0.5780) is lower than its rate (0.6800) because the business-hours
> penalty applies outside 9am–5pm UTC.

**Philippines** (`PHP 2000.00`)
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | gcash | 0.8100 | 0.8100 | 0 |
| 2 | grabpay | 0.7500 | 0.7500 | 0 |
| 3 | credit_card | 0.1000 | 0.1000 | 0 |

---

## Step 2 — Seed 600 historical transactions

```
Seeded 600 transactions across 5 countries.
```

Distribution:
- BR: 90 pix, 35 credit_card, 25 boleto
- MX: 90 oxxo, 35 credit_card, 25 spei
- PH: 45 gcash, 35 grabpay, 20 credit_card
- CO: 50 pse, 30 credit_card, 20 neki
- JP: 55 paypay, 25 seven_eleven, 20 credit_card

---

## Step 3 — Recommendations AFTER seeding (empirical data in play)

Scores now blend the prior with real observed outcomes via Bayesian smoothing:
`bayesian_rate = (successes + 10 × prior) / (attempts + 10)`

**Brazil** (`BRL 150.00`) — 150 transactions
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | pix | 0.8450 | 0.8450 | 90 |
| 2 | boleto | 0.7286 | 0.7286 | 25 |
| 3 | credit_card | 0.1444 | 0.1444 | 35 |

**Mexico** (`MXN 500.00`) — 150 transactions
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | oxxo | 0.7220 | 0.7220 | 90 |
| 2 | spei | 0.5051 | 0.5942 | 25 |
| 3 | credit_card | 0.2889 | 0.2889 | 35 |

**Philippines** (`PHP 2000.00`) — 100 transactions
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | grabpay | 0.7889 | 0.7889 | 35 |
| 2 | gcash | 0.7655 | 0.7655 | 45 |
| 3 | credit_card | 0.2667 | 0.2667 | 20 |

> Observation: In this run, grabpay edged out gcash after seeding — the empirical
> data slightly outperformed gcash's prior, flipping their order.

---

## Step 4 — Inject 10 fabricated credit_card successes for Brazil

```
Inserted 10 SUCCESS outcomes for BR/credit_card
```

Brazil's credit_card now has 45 total attempts (35 seeded + 10 injected),
all 10 new ones marked as successful.

---

## Step 5 — Brazil after credit_card boost

**Brazil** (`BRL 150.00`) — after injection
| Rank | Method | Score | Rate | Data Points |
|------|--------|-------|------|-------------|
| 1 | pix | 0.8450 | 0.8450 | 90 |
| 2 | boleto | 0.7286 | 0.7286 | 25 |
| 3 | credit_card | **0.3000** | **0.3000** | 45 |

**credit_card score before injection:** 0.1444
**credit_card score after injection:** 0.3000
**Change:** +0.1556 (+107%)

The ranking did not change (pix and boleto are still far ahead), but the score
more than doubled — demonstrating that the algorithm learns continuously from
new outcomes without requiring a retrain or restart.

---

## Key Takeaways

1. **With no data**, the router falls back to expert priors — it's never blind.
2. **After seeding**, empirical rates take over and scores closely track real observed outcomes.
3. **Injecting outcomes** updates scores immediately on the next request — no batch jobs or retraining needed.
4. **Rankings are stable** — a small number of transactions shifts scores but doesn't flip rankings dominated by strong priors.
