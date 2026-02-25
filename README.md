# RouteFlow — Intelligent Payment Method Router

A dynamic payment method routing service that eliminates checkout abandonment caused by country-blind payment cascades. RouteFlow ranks payment methods by **predicted success probability** using Bayesian scoring on real transaction outcomes.

---

## The Problem

Standard checkout flows try payment methods in the same order for every country — typically `credit_card` first. In LatAm and SEA markets, credit card success rates are 8–15%, while local methods succeed 70–85% of the time. Users abandon before the right method is ever offered.

**RouteFlow fixes this** by learning from historical outcomes and serving the best method first, every time.

---

## How It Works

RouteFlow uses **Bayesian smoothing** to score each payment method:

```
bayesian_rate = (successes + α × prior) / (attempts + α)
score         = bayesian_rate × amount_factor × time_factor
```

- **Prior knowledge** (domain expertise) is used when no data exists
- **Empirical data** progressively overrides the prior as transactions accumulate
- With `α=10`, after ~10 real transactions, empirical rates start to dominate
- **Amount factor** penalizes methods outside their typical transaction range
- **Time factor** boosts bank transfers during business hours, penalizes outside

### Example: Brazil

| Method | Prior | After 90 PIX txns (86% success) |
|---|---|---|
| pix | 0.850 | **0.861** (data confirms prior) |
| bank_transfer | 0.400 | 0.421 |
| credit_card | 0.150 | **0.143** (data confirms poor performance) |

---

## Tech Stack

| Layer | Choice |
|---|---|
| Runtime | Python 3.9+ |
| Framework | FastAPI (auto Swagger UI) |
| Database | SQLite (zero config) |
| Server | Uvicorn |

---

## Project Structure

```
routeflow-payment-router/
├── README.md
├── requirements.txt
├── app/
│   ├── main.py          # FastAPI app + all route handlers
│   ├── database.py      # SQLite init, schema, connection helper
│   ├── models.py        # Pydantic request/response models
│   ├── router.py        # Bayesian routing algorithm
│   ├── analytics.py     # Analytics aggregation queries
│   └── config.py        # Country-method configs, priors, amount rules
└── scripts/
    ├── seed_data.py     # Generate 600 synthetic transactions
    └── demo.py          # End-to-end learning demonstration
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install fastapi uvicorn
```

### 2. Start the server

```bash
uvicorn app.main:app --reload
```

The API is now live at `http://localhost:8000`
Swagger UI: `http://localhost:8000/docs`

### 3. Seed historical data (optional but recommended)

```bash
python scripts/seed_data.py
```

Seeds 600 transactions across 5 countries with realistic success patterns.

### 4. Run the learning demo

```bash
python scripts/demo.py
```

### 5. Run the test suite

Install test dependencies and run all 102 tests:

```bash
pip install pytest httpx
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database — they are fully isolated and do not touch `routeflow.db`. No server needs to be running.

To run a specific module:

```bash
python -m pytest tests/test_recommendations.py -v   # routing logic
python -m pytest tests/test_transactions.py -v      # transaction recording
python -m pytest tests/test_analytics.py -v         # analytics filters
python -m pytest tests/test_learning.py -v          # Bayesian learning behaviour
python -m pytest tests/test_health.py -v            # health endpoint
```

---

## API Reference

### `POST /api/v1/recommendations`

Get ranked payment methods for a transaction context.

```bash
curl -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 150.0}'
```

**Response:**
```json
{
  "country": "BR",
  "currency": "BRL",
  "amount": 150.0,
  "recommendations": [
    {"method": "pix", "estimated_success_rate": 0.861, "score": 0.861, "data_points": 90},
    {"method": "bank_transfer", "estimated_success_rate": 0.421, "score": 0.421, "data_points": 25},
    {"method": "credit_card", "estimated_success_rate": 0.143, "score": 0.143, "data_points": 35}
  ]
}
```

---

### `POST /api/v1/transactions`

Record a transaction outcome to feed the learning loop. **This is the primary way RouteFlow improves over time.**

Every recorded outcome immediately affects the next recommendation — there is no batch job or retraining step. The Bayesian formula re-evaluates on every request using the live transaction count in the database.

**Both successes and failures matter.** A `success: false` outcome is just as valuable as a success: it teaches the router which methods underperform for a given country, pulling their score down on subsequent requests.

**How many transactions before the prior is overridden?** With `α=10` (the Bayesian weight given to the prior), after roughly 10 real transactions the empirical rate starts to have meaningful influence. After ~50 transactions, real data dominates and the prior becomes a minor factor.

**Backfilling historical data** is supported via the optional `timestamp` field. Pass an ISO 8601 datetime to record past outcomes — useful for importing data from an existing system on first deploy.

```bash
# Record a successful transaction
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "MX", "currency": "MXN", "amount": 500.0, "payment_method": "oxxo", "success": true}'

# Record a failed transaction (equally important for learning)
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 200.0, "payment_method": "credit_card", "success": false}'

# Backfill a historical outcome using an explicit timestamp
curl -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 150.0, "payment_method": "pix", "success": true, "timestamp": "2024-06-15T10:30:00Z"}'
```

**Response:**
```json
{"id": "a3f7c2d1-...", "status": "recorded"}
```

---

### `GET /api/v1/analytics`

Aggregate success metrics with optional filters.

```bash
# All countries
curl http://localhost:8000/api/v1/analytics

# Brazil only, date range
curl "http://localhost:8000/api/v1/analytics?country=BR&from_date=2024-01-01&to_date=2024-12-31"
```

**Response:**
```json
{
  "filters": {"country": "BR"},
  "metrics": [
    {
      "country": "BR",
      "payment_method": "pix",
      "total_attempts": 90,
      "total_success": 77,
      "success_rate": 0.856,
      "avg_amount": 384.20
    }
  ]
}
```

---

### `GET /api/v1/health`

```bash
curl http://localhost:8000/api/v1/health
```

```json
{"status": "ok", "version": "1.0.0", "db_status": "ok"}
```

---

## Supported Countries & Methods

| Country | Methods (ranked by prior success rate) |
|---|---|
| 🇧🇷 Brazil (BR/BRL) | PIX (85%), bank_transfer (40%), credit_card (15%) |
| 🇲🇽 Mexico (MX/MXN) | OXXO (72%), bank_transfer (35%), credit_card (20%) |
| 🇵🇭 Philippines (PH/PHP) | GCash (81%), GrabPay (75%), credit_card (10%) |
| 🇨🇴 Colombia (CO/COP) | PSE (70%), bank_transfer (35%), credit_card (20%) |
| 🇰🇪 Kenya (KE/KES) | M-Pesa (82%), bank_transfer (30%), credit_card (15%) |

---

## Key Design Decisions

- **SQLite over Postgres:** Zero infrastructure setup, single file, easy to demo and reset
- **Bayesian over ML:** Interpretable, works with small data, clearly demonstrates learning, no sklearn dependency
- **α=10:** Balances responsiveness (learns fast) vs stability (doesn't flip on 1–2 transactions)
- **Priors in config.py not DB:** Keeps them readable/editable without migrations
- **FastAPI for auto-docs:** The Swagger UI at `/docs` is itself a demonstration tool

---

## Verification Checklist

- [ ] `pip install fastapi uvicorn` → `uvicorn app.main:app --reload`
- [ ] Navigate to `http://localhost:8000/docs` — Swagger UI shows all endpoints
- [ ] `python scripts/seed_data.py` — seeds 600 transactions
- [ ] `POST /api/v1/recommendations` with `{"country":"BR","currency":"BRL","amount":100}` → PIX ranked first
- [ ] `POST /api/v1/recommendations` with `{"country":"MX","currency":"MXN","amount":200}` → OXXO ranked first
- [ ] POST 10 `credit_card` success outcomes for Brazil → re-query → score rises
- [ ] `GET /api/v1/analytics?country=BR` → metrics match seed data
- [ ] `python scripts/demo.py` → end-to-end learning demonstration
