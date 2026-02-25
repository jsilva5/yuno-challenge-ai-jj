"""
Bayesian payment method router.

Scoring formula:
    bayesian_rate = (successes + alpha * prior) / (attempts + alpha)
    score = bayesian_rate * amount_factor * time_factor

With alpha=10, the empirical rate starts dominating after ~10 real transactions.
"""

from datetime import datetime, timezone
from typing import List

from app.config import (
    COUNTRY_METHODS,
    PRIOR_RATES,
    AMOUNT_RANGES,
    CURRENCY_TO_USD,
    BUSINESS_HOURS_METHODS,
    BUSINESS_HOURS_BONUS,
    OFF_HOURS_PENALTY,
    ALPHA,
)
from app.models import MethodRecommendation


def get_amount_factor(method: str, amount_usd: float) -> float:
    """Return a multiplier based on whether the amount fits the method's typical range."""
    if method not in AMOUNT_RANGES:
        return 1.0
    lo, hi = AMOUNT_RANGES[method]
    if amount_usd < lo:
        # Below minimum — gentle penalty proportional to how far below
        return max(0.5, amount_usd / lo)
    if amount_usd > hi:
        # Above maximum — steeper penalty
        return max(0.4, hi / amount_usd)
    return 1.0


def get_time_factor(method: str, hour: int) -> float:
    """Return a multiplier based on business hours for certain payment methods."""
    if method not in BUSINESS_HOURS_METHODS:
        return 1.0
    if 9 <= hour < 17:
        return BUSINESS_HOURS_BONUS
    return OFF_HOURS_PENALTY


def compute_score(country: str, method: str, amount_usd: float, hour: int, conn) -> tuple[float, int]:
    """
    Compute the Bayesian score for a (country, method) pair.
    Returns (score, data_points).
    """
    prior = PRIOR_RATES.get((country, method), 0.5)

    row = conn.execute(
        "SELECT COUNT(*), SUM(success) FROM transactions WHERE country=? AND payment_method=?",
        (country, method),
    ).fetchone()

    attempts = row[0] or 0
    successes = row[1] or 0

    bayesian_rate = (successes + ALPHA * prior) / (attempts + ALPHA)
    amount_factor = get_amount_factor(method, amount_usd)
    time_factor = get_time_factor(method, hour)

    score = bayesian_rate * amount_factor * time_factor
    return round(score, 4), attempts


def get_recommendations(country: str, currency: str, amount: float, conn) -> List[MethodRecommendation]:
    """
    Return payment methods for the given country ranked by Bayesian score (descending).
    """
    methods = COUNTRY_METHODS.get(country)
    if not methods:
        return []

    # Normalize amount to USD for range checks
    usd_rate = CURRENCY_TO_USD.get(currency, 1.0)
    amount_usd = amount * usd_rate

    hour = datetime.now(timezone.utc).hour

    scored = []
    for method in methods:
        score, data_points = compute_score(country, method, amount_usd, hour, conn)
        scored.append(
            MethodRecommendation(
                method=method,
                estimated_success_rate=round(
                    (score / (get_amount_factor(method, amount_usd) * get_time_factor(method, hour))),
                    4,
                ),
                score=score,
                data_points=data_points,
            )
        )

    scored.sort(key=lambda r: r.score, reverse=True)
    return scored
