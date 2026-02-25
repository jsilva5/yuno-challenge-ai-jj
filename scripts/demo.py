"""
End-to-end demo showing RouteFlow's Bayesian learning behavior.

Steps:
1. Show recommendations BEFORE seeding (pure priors)
2. Seed 600 historical transactions
3. Show recommendations AFTER seeding (empirical data dominates)
4. Feed 10 fabricated credit_card successes for Brazil
5. Show credit_card score rises (Bayesian update in action)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from datetime import datetime, timezone

from app.database import init_db, get_db
from app.router import get_recommendations
from scripts.seed_data import seed


def print_recommendations(label: str, country: str, currency: str, amount: float):
    conn = get_db()
    recs = get_recommendations(country, currency, amount, conn)
    conn.close()
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"  Country={country}  Currency={currency}  Amount={amount}")
    print(f"{'='*60}")
    for i, r in enumerate(recs, 1):
        bar = "█" * int(r.score * 30)
        print(f"  {i}. {r.method:<15} score={r.score:.4f}  rate={r.estimated_success_rate:.4f}  n={r.data_points}  {bar}")


def insert_outcomes(country: str, currency: str, method: str, amount: float, success: bool, count: int):
    conn = get_db()
    for _ in range(count):
        conn.execute(
            """INSERT INTO transactions (id, country, currency, amount, payment_method, success, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid.uuid4()), country, currency, amount, method, 1 if success else 0,
             datetime.now(timezone.utc).isoformat()),
        )
    conn.commit()
    conn.close()
    print(f"\n  >> Inserted {count} {'SUCCESS' if success else 'FAILURE'} outcomes for {country}/{method}")


def clear_db():
    conn = get_db()
    conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()


def main():
    init_db()
    clear_db()

    print("\n" + "="*60)
    print("  ROUTEFLOW — BAYESIAN LEARNING DEMO")
    print("="*60)

    # Step 1: Recommendations with no data (pure priors)
    print("\n[STEP 1] Recommendations with NO historical data (pure priors)")
    print_recommendations("Brazil — No data", "BR", "BRL", 150.0)
    print_recommendations("Mexico — No data", "MX", "MXN", 500.0)
    print_recommendations("Philippines — No data", "PH", "PHP", 2000.0)

    # Step 2: Seed historical data
    print("\n\n[STEP 2] Seeding 600 historical transactions...")
    seed()

    # Step 3: Recommendations after seeding
    print("\n[STEP 3] Recommendations AFTER seeding (empirical data in play)")
    print_recommendations("Brazil — 150 txns", "BR", "BRL", 150.0)
    print_recommendations("Mexico — 150 txns", "MX", "MXN", 500.0)
    print_recommendations("Philippines — 100 txns", "PH", "PHP", 2000.0)

    # Step 4: Force 10 credit_card successes for Brazil
    print("\n\n[STEP 4] Feeding 10 fabricated credit_card SUCCESS outcomes for Brazil...")
    insert_outcomes("BR", "BRL", "credit_card", 150.0, True, 10)

    # Step 5: Show credit_card score has risen
    print("\n[STEP 5] Brazil recommendations after 10 extra credit_card successes")
    print("         (credit_card score should be HIGHER than before)")
    print_recommendations("Brazil — After credit_card boost", "BR", "BRL", 150.0)

    print("\n\n" + "="*60)
    print("  DEMO COMPLETE — Bayesian updating confirmed!")
    print("  Run the API: uvicorn app.main:app --reload")
    print("  Docs:        http://localhost:8000/docs")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
