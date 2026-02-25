"""
Seed the RouteFlow database with 600 synthetic transactions across 5 countries.
Reflects realistic success rates:
  BR (150): PIX 86%, credit_card 14%, bank_transfer 42%
  MX (150): OXXO 72%, credit_card 18%, bank_transfer 37%
  PH (100): GCash 80%, GrabPay 74%, credit_card 9%
  CO (100): PSE 69%, credit_card 19%, bank_transfer 34%
  KE (100): M-Pesa 83%, credit_card 14%, bank_transfer 31%
"""

import sys
import os
import random
import math
from datetime import datetime, timedelta, timezone

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, get_db

# Seed config: (country, currency, method, count, success_rate)
SEED_CONFIG = [
    # Brazil
    ("BR", "BRL", "pix",           90, 0.86),
    ("BR", "BRL", "credit_card",   35, 0.14),
    ("BR", "BRL", "bank_transfer", 25, 0.42),
    # Mexico
    ("MX", "MXN", "oxxo",          90, 0.72),
    ("MX", "MXN", "credit_card",   35, 0.18),
    ("MX", "MXN", "bank_transfer", 25, 0.37),
    # Philippines
    ("PH", "PHP", "gcash",         45, 0.80),
    ("PH", "PHP", "grabpay",       35, 0.74),
    ("PH", "PHP", "credit_card",   20, 0.09),
    # Colombia
    ("CO", "COP", "pse",           50, 0.69),
    ("CO", "COP", "credit_card",   30, 0.19),
    ("CO", "COP", "bank_transfer", 20, 0.34),
    # Kenya
    ("KE", "KES", "mpesa",         55, 0.83),
    ("KE", "KES", "credit_card",   25, 0.14),
    ("KE", "KES", "bank_transfer", 20, 0.31),
]

# Typical amount ranges per currency (min, max)
AMOUNT_RANGES = {
    "BRL": (20, 2000),
    "MXN": (100, 15000),
    "PHP": (200, 15000),
    "COP": (10000, 2000000),
    "KES": (200, 50000),
}


def log_normal_amount(lo: float, hi: float) -> float:
    """Generate a log-normal distributed amount within [lo, hi]."""
    log_lo, log_hi = math.log(lo), math.log(hi)
    mu = (log_lo + log_hi) / 2
    sigma = (log_hi - log_lo) / 4
    val = math.exp(random.gauss(mu, sigma))
    return round(max(lo, min(hi, val)), 2)


def random_timestamp(days_back: int = 90, method: str = "") -> datetime:
    """
    Generate a random timestamp in the last `days_back` days.
    Bank transfers are weighted toward business hours (9-17).
    """
    base = datetime.now(timezone.utc) - timedelta(days=days_back)
    offset_seconds = random.randint(0, days_back * 86400)
    ts = base + timedelta(seconds=offset_seconds)

    if method in ("bank_transfer", "pse"):
        # Bias toward business hours
        if random.random() < 0.70:
            ts = ts.replace(hour=random.randint(9, 16), minute=random.randint(0, 59))

    return ts


def seed():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    # Clear existing seed data
    cursor.execute("DELETE FROM transactions")

    import uuid

    total = 0
    for country, currency, method, count, success_rate in SEED_CONFIG:
        lo, hi = AMOUNT_RANGES[currency]
        for _ in range(count):
            txn_id = str(uuid.uuid4())
            amount = log_normal_amount(lo, hi)
            success = 1 if random.random() < success_rate else 0
            ts = random_timestamp(method=method)

            cursor.execute(
                """
                INSERT INTO transactions (id, country, currency, amount, payment_method, success, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (txn_id, country, currency, amount, method, success, ts.isoformat()),
            )
            total += 1

    conn.commit()
    conn.close()
    print(f"Seeded {total} transactions across 5 countries.")


if __name__ == "__main__":
    seed()
