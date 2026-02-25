# Manual Testing Guide

This guide walks through every endpoint step by step using `curl`. Run commands from the project root.

---

## Prerequisites

```bash
# Install dependencies (once)
pip install fastapi uvicorn

# Start the server
python3 -m uvicorn app.main:app --reload --port 8000
```

The server runs at `http://localhost:8000`.
Swagger UI (interactive): `http://localhost:8000/docs`

---

## Step 1 — Health Check

```bash
curl http://localhost:8000/api/v1/health
```

Expected:
```json
{"status": "ok", "version": "1.0.0", "db_status": "ok"}
```

---

## Step 2 — Seed Historical Data

```bash
python3 scripts/seed_data.py
```

Expected: `Seeded 600 transactions across 5 countries.`

This populates the database with realistic transaction outcomes so the Bayesian router has data to learn from.

---

## Step 3 — Recommendations (all 5 countries)

### Brazil — PIX should rank first (~85% success)
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 150.0}'
```

### Mexico — OXXO should rank first (~72% success)
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "MX", "currency": "MXN", "amount": 200.0}'
```

### Philippines — GCash should rank first (~81% success)
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "PH", "currency": "PHP", "amount": 500.0}'
```

### Colombia — PSE should rank first (~70% success)
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "CO", "currency": "COP", "amount": 300.0}'
```

### Kenya — M-Pesa should rank first (~82% success)
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "KE", "currency": "KES", "amount": 100.0}'
```

---

## Step 4 — Record a Transaction Outcome

Calling this endpoint is how RouteFlow learns. Each recorded outcome is persisted immediately and influences the very next recommendation — no restart or retraining required.

**Record a successful transaction:**
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "MX", "currency": "MXN", "amount": 500.0, "payment_method": "oxxo", "success": true}'
```

Expected:
```json
{"id": "<uuid>", "status": "recorded"}
```

**Record a failed transaction** — failures are equally important. They pull a method's score down, teaching the router what doesn't work:
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 200.0, "payment_method": "credit_card", "success": false}'
```

**Backfill a historical outcome** using the optional `timestamp` field — useful when importing data from an existing system:
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 150.0, "payment_method": "pix", "success": true, "timestamp": "2024-06-15T10:30:00Z"}'
```

---

## Step 5 — Demonstrate Learning Behavior

This shows the Bayesian router updating scores in real time as new outcomes are recorded.

The router blends a **prior** (domain knowledge) with **empirical data** using the formula:

```
bayesian_rate = (successes + α × prior) / (attempts + α)
```

With `α=10`, roughly 10 transactions begin shifting the score away from the prior. After ~50 transactions, real data dominates. The update is immediate — each new transaction changes the score on the very next recommendation call.

**1. Check Brazil `credit_card` score before feeding data:**
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 100.0}'
```
Note the `score` and `data_points` for `credit_card`. With no data, the score equals the prior (0.15).

**2. Feed 10 successful `credit_card` outcomes for Brazil:**
```bash
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/api/v1/transactions \
    -H "Content-Type: application/json" \
    -d '{"country": "BR", "currency": "BRL", "amount": 100.0, "payment_method": "credit_card", "success": true}' \
    > /dev/null
done
echo "Done feeding 10 successes"
```

**3. Check the score again — it should be higher:**
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 100.0}'
```

With 10 successes out of 10 attempts, the new Bayesian rate is: `(10 + 10×0.15) / (10 + 10) = 0.575` — up from 0.15. The `data_points` field will now show `10`, confirming the empirical data was incorporated.

**4. Observe the inverse — feed failures to push a score down:**
```bash
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/api/v1/transactions \
    -H "Content-Type: application/json" \
    -d '{"country": "BR", "currency": "BRL", "amount": 100.0, "payment_method": "pix", "success": false}' \
    > /dev/null
done
echo "Done feeding 10 failures"
```

Re-query recommendations — `pix`'s score will drop from its prior of 0.85 toward the observed failure rate.

---

## Step 6 — Analytics

### All countries
```bash
curl -s http://localhost:8000/api/v1/analytics
```

### Filter by country
```bash
curl -s "http://localhost:8000/api/v1/analytics?country=BR"
curl -s "http://localhost:8000/api/v1/analytics?country=MX"
```

### Filter by date range
```bash
curl -s "http://localhost:8000/api/v1/analytics?country=BR&from_date=2024-01-01&to_date=2024-12-31"
```

Expected response shape:
```json
{
  "filters": {"country": "BR"},
  "metrics": [
    {
      "country": "BR",
      "payment_method": "pix",
      "total_attempts": 90,
      "total_success": 78,
      "success_rate": 0.867,
      "avg_amount": 349.64
    }
  ]
}
```

---

## Step 7 — End-to-End Demo Script

```bash
python3 scripts/demo.py
```

This script shows the full learning cycle:
1. Prints recommendations before seeding
2. Seeds 600 historical transactions
3. Prints recommendations after — scores shift toward empirical data
4. Feeds 10 fabricated `credit_card` successes for Brazil
5. Shows the score rising (Bayesian update in action)

---

## Reset the Database

To start fresh and re-run tests from a clean state:

```bash
rm routeflow.db
python3 scripts/seed_data.py
```

The database is recreated automatically when the server starts.

---

## Quick Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Liveness check |
| POST | `/api/v1/recommendations` | Get ranked payment methods |
| POST | `/api/v1/transactions` | Record a transaction outcome |
| GET | `/api/v1/analytics` | Aggregate success metrics |
| GET | `/docs` | Swagger UI (interactive testing) |
