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

```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "MX", "currency": "MXN", "amount": 500.0, "payment_method": "oxxo", "success": true}'
```

Expected:
```json
{"id": "<uuid>", "status": "recorded"}
```

Record a failed transaction:
```bash
curl -s -X POST http://localhost:8000/api/v1/transactions \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 200.0, "payment_method": "credit_card", "success": false}'
```

---

## Step 5 — Demonstrate Learning Behavior

This shows the Bayesian router updating scores as new outcomes are recorded.

**Check Brazil credit_card score before:**
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 100.0}'
```
Note the `score` for `credit_card`.

**Feed 10 successful credit_card outcomes for Brazil:**
```bash
for i in $(seq 1 10); do
  curl -s -X POST http://localhost:8000/api/v1/transactions \
    -H "Content-Type: application/json" \
    -d '{"country": "BR", "currency": "BRL", "amount": 100.0, "payment_method": "credit_card", "success": true}' \
    > /dev/null
done
echo "Done feeding 10 successes"
```

**Check Brazil credit_card score after — it should be higher:**
```bash
curl -s -X POST http://localhost:8000/api/v1/recommendations \
  -H "Content-Type: application/json" \
  -d '{"country": "BR", "currency": "BRL", "amount": 100.0}'
```

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
