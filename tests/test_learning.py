"""
Tests for the Bayesian learning behaviour of the routing algorithm.

These tests verify that:
- Prior rates are used when no transaction data exists
- Scores rise after recording successful outcomes
- Scores fall after recording failed outcomes
- Local methods outrank credit_card from the start (prior knowledge)
- The system converges toward empirical data as volume grows
- Learning for one country does not bleed into another

Bayesian formula (alpha=10):
    bayesian_rate = (successes + 10 * prior) / (attempts + 10)

For BR/pix with prior=0.85:
    0 txns  → (0  + 8.5) / (0  + 10) = 0.85
    10 successes → (10 + 8.5) / (20)  = 0.925
    10 failures  → (0  + 8.5) / (20)  = 0.425

All tests use amounts well within method limits (amount_factor=1.0).
estimated_success_rate already strips amount/time factors for clean comparison.
"""

import pytest
from tests.conftest import seed_transaction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_recommendations(client, country, currency, amount):
    r = client.post(
        "/api/v1/recommendations",
        json={"country": country, "currency": currency, "amount": amount},
    )
    assert r.status_code == 200
    return {rec["method"]: rec for rec in r.json()["recommendations"]}


def post_outcomes(client, country, currency, amount, method, success, n):
    for _ in range(n):
        client.post(
            "/api/v1/transactions",
            json={
                "country": country,
                "currency": currency,
                "amount": amount,
                "payment_method": method,
                "success": success,
            },
        )


# ---------------------------------------------------------------------------
# Prior rates used when no data exists
# ---------------------------------------------------------------------------

def test_pix_prior_rate_with_no_data(client):
    """BR/pix prior = 0.85 — should be the estimated_success_rate on empty DB."""
    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert abs(recs["pix"]["estimated_success_rate"] - 0.85) < 0.001


def test_credit_card_prior_rate_brazil_with_no_data(client):
    """BR/credit_card prior = 0.15."""
    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert abs(recs["credit_card"]["estimated_success_rate"] - 0.15) < 0.001


def test_oxxo_prior_rate_with_no_data(client):
    """MX/oxxo prior = 0.72."""
    recs = get_recommendations(client, "MX", "MXN", 500.0)
    assert abs(recs["oxxo"]["estimated_success_rate"] - 0.72) < 0.001


def test_gcash_prior_rate_with_no_data(client):
    """PH/gcash prior = 0.81."""
    recs = get_recommendations(client, "PH", "PHP", 100.0)
    assert abs(recs["gcash"]["estimated_success_rate"] - 0.81) < 0.001


# ---------------------------------------------------------------------------
# Local methods outrank credit_card from day one
# ---------------------------------------------------------------------------

def test_pix_outranks_credit_card_brazil_no_data(client):
    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert recs["pix"]["score"] > recs["credit_card"]["score"]


def test_oxxo_outranks_credit_card_mexico_no_data(client):
    recs = get_recommendations(client, "MX", "MXN", 500.0)
    assert recs["oxxo"]["score"] > recs["credit_card"]["score"]


def test_gcash_outranks_credit_card_philippines_no_data(client):
    recs = get_recommendations(client, "PH", "PHP", 100.0)
    assert recs["gcash"]["score"] > recs["credit_card"]["score"]


# ---------------------------------------------------------------------------
# Score rises after recording successes
# ---------------------------------------------------------------------------

def test_credit_card_score_rises_after_successes(client):
    """
    Feed 20 successful credit_card outcomes for Brazil.
    With alpha=10: (20 + 10*0.15)/(20+10) = 21.5/30 ≈ 0.717
    — well above the prior of 0.15.
    """
    before = get_recommendations(client, "BR", "BRL", 500.0)
    post_outcomes(client, "BR", "BRL", 500.0, "credit_card", True, 20)
    after = get_recommendations(client, "BR", "BRL", 500.0)

    assert after["credit_card"]["estimated_success_rate"] > \
           before["credit_card"]["estimated_success_rate"]


def test_pix_score_rises_further_after_successes(client):
    """Confirming pix with 30 successes pushes its rate above the prior."""
    before = get_recommendations(client, "BR", "BRL", 500.0)
    post_outcomes(client, "BR", "BRL", 500.0, "pix", True, 30)
    after = get_recommendations(client, "BR", "BRL", 500.0)

    assert after["pix"]["estimated_success_rate"] > \
           before["pix"]["estimated_success_rate"]


# ---------------------------------------------------------------------------
# Score falls after recording failures
# ---------------------------------------------------------------------------

def test_pix_score_drops_after_failures(client):
    """
    Feed 30 pix failures for Brazil.
    (0 + 10*0.85)/(30+10) = 8.5/40 = 0.2125 — far below the prior of 0.85.
    """
    before = get_recommendations(client, "BR", "BRL", 500.0)
    post_outcomes(client, "BR", "BRL", 500.0, "pix", False, 30)
    after = get_recommendations(client, "BR", "BRL", 500.0)

    assert after["pix"]["estimated_success_rate"] < \
           before["pix"]["estimated_success_rate"]


def test_oxxo_score_drops_after_failures(client):
    post_outcomes(client, "MX", "MXN", 200.0, "oxxo", False, 20)
    recs = get_recommendations(client, "MX", "MXN", 200.0)
    # After 20 failures, oxxo rate should be well below its 0.72 prior
    assert recs["oxxo"]["estimated_success_rate"] < 0.72


# ---------------------------------------------------------------------------
# Ranking changes after enough contradicting data
# ---------------------------------------------------------------------------

def test_credit_card_can_outrank_pix_after_many_successes_and_failures(client):
    """
    Force an extreme scenario: 50 credit_card successes + 50 pix failures.
    Credit card should eventually overtake pix in the ranking.
    """
    post_outcomes(client, "BR", "BRL", 500.0, "credit_card", True, 50)
    post_outcomes(client, "BR", "BRL", 500.0, "pix", False, 50)

    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert recs["credit_card"]["estimated_success_rate"] > \
           recs["pix"]["estimated_success_rate"]


# ---------------------------------------------------------------------------
# Data isolation between countries
# ---------------------------------------------------------------------------

def test_brazil_learning_does_not_affect_mexico(client):
    """Recording outcomes for BR should not change MX scores."""
    mx_before = get_recommendations(client, "MX", "MXN", 200.0)

    # Feed lots of failures for BR/credit_card
    post_outcomes(client, "BR", "BRL", 500.0, "credit_card", False, 30)

    mx_after = get_recommendations(client, "MX", "MXN", 200.0)
    assert mx_after["credit_card"]["estimated_success_rate"] == \
           mx_before["credit_card"]["estimated_success_rate"]


def test_japan_learning_does_not_affect_brazil(client):
    """Recording outcomes for JP should not change BR scores."""
    br_before = get_recommendations(client, "BR", "BRL", 500.0)

    post_outcomes(client, "JP", "JPY", 5000.0, "credit_card", False, 30)

    br_after = get_recommendations(client, "BR", "BRL", 500.0)
    assert br_after["credit_card"]["estimated_success_rate"] == \
           br_before["credit_card"]["estimated_success_rate"]


# ---------------------------------------------------------------------------
# Data point count reflects recorded transactions
# ---------------------------------------------------------------------------

def test_data_points_increase_with_transactions(client):
    post_outcomes(client, "BR", "BRL", 500.0, "pix", True, 5)
    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert recs["pix"]["data_points"] == 5


def test_data_points_count_successes_and_failures(client):
    post_outcomes(client, "BR", "BRL", 500.0, "pix", True, 3)
    post_outcomes(client, "BR", "BRL", 500.0, "pix", False, 7)
    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert recs["pix"]["data_points"] == 10


def test_data_points_per_method_are_independent(client):
    post_outcomes(client, "BR", "BRL", 500.0, "pix", True, 5)
    post_outcomes(client, "BR", "BRL", 500.0, "credit_card", True, 3)
    recs = get_recommendations(client, "BR", "BRL", 500.0)
    assert recs["pix"]["data_points"] == 5
    assert recs["credit_card"]["data_points"] == 3
