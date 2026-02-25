"""
Tests for POST /api/v1/recommendations

Covers:
- Happy path for all 5 supported countries
- Correct priority ordering (local method ranked first)
- Response structure validation
- Input validation (422 errors)
- Unknown country (404)
- Country code normalisation (lowercase input)
- Amount factor penalties for out-of-range amounts
- Unknown currency code falls back gracefully
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def recommend(client, country, currency, amount):
    return client.post(
        "/api/v1/recommendations",
        json={"country": country, "currency": currency, "amount": amount},
    )


# ---------------------------------------------------------------------------
# Happy path — correct top method per country
# ---------------------------------------------------------------------------

def test_brazil_pix_ranked_first(client):
    r = recommend(client, "BR", "BRL", 150.0)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["method"] == "pix"


def test_mexico_oxxo_ranked_first(client):
    r = recommend(client, "MX", "MXN", 200.0)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["method"] == "oxxo"


def test_philippines_gcash_ranked_first(client):
    r = recommend(client, "PH", "PHP", 500.0)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["method"] == "gcash"


def test_colombia_pse_ranked_first(client):
    r = recommend(client, "CO", "COP", 300_000.0)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["method"] == "pse"


def test_japan_paypay_ranked_first(client):
    r = recommend(client, "JP", "JPY", 5000.0)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["method"] == "paypay"


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------

def test_response_contains_country_currency_amount(client):
    r = recommend(client, "BR", "BRL", 150.0)
    data = r.json()
    assert data["country"] == "BR"
    assert data["currency"] == "BRL"
    assert data["amount"] == 150.0


def test_each_recommendation_has_required_fields(client):
    r = recommend(client, "BR", "BRL", 150.0)
    for rec in r.json()["recommendations"]:
        assert "method" in rec
        assert "estimated_success_rate" in rec
        assert "score" in rec
        assert "data_points" in rec


def test_recommendations_are_sorted_by_score_descending(client):
    r = recommend(client, "BR", "BRL", 150.0)
    scores = [rec["score"] for rec in r.json()["recommendations"]]
    assert scores == sorted(scores, reverse=True)


def test_brazil_returns_three_methods(client):
    r = recommend(client, "BR", "BRL", 150.0)
    assert len(r.json()["recommendations"]) == 3


def test_data_points_zero_on_empty_db(client):
    r = recommend(client, "BR", "BRL", 150.0)
    for rec in r.json()["recommendations"]:
        assert rec["data_points"] == 0


def test_estimated_success_rate_between_zero_and_one(client):
    r = recommend(client, "BR", "BRL", 150.0)
    for rec in r.json()["recommendations"]:
        assert 0.0 <= rec["estimated_success_rate"] <= 1.0


# ---------------------------------------------------------------------------
# Country code normalisation
# ---------------------------------------------------------------------------

def test_lowercase_country_is_normalised(client):
    """'br' should be treated the same as 'BR'."""
    r = recommend(client, "br", "BRL", 150.0)
    assert r.status_code == 200
    assert r.json()["recommendations"][0]["method"] == "pix"


def test_mixed_case_country_is_normalised(client):
    r = recommend(client, "bR", "BRL", 150.0)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Unknown / unsupported country
# ---------------------------------------------------------------------------

def test_unknown_country_returns_404(client):
    r = recommend(client, "US", "USD", 100.0)
    assert r.status_code == 404


def test_unknown_country_error_message_mentions_country(client):
    r = recommend(client, "ZZ", "USD", 100.0)
    assert r.status_code == 404
    assert "ZZ" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Validation errors (422 Unprocessable Entity)
# ---------------------------------------------------------------------------

def test_missing_country_returns_422(client):
    r = client.post("/api/v1/recommendations",
                    json={"currency": "BRL", "amount": 100.0})
    assert r.status_code == 422


def test_missing_currency_returns_422(client):
    r = client.post("/api/v1/recommendations",
                    json={"country": "BR", "amount": 100.0})
    assert r.status_code == 422


def test_missing_amount_returns_422(client):
    r = client.post("/api/v1/recommendations",
                    json={"country": "BR", "currency": "BRL"})
    assert r.status_code == 422


def test_empty_body_returns_422(client):
    r = client.post("/api/v1/recommendations", json={})
    assert r.status_code == 422


def test_country_too_long_returns_422(client):
    """Country must be exactly 2 characters (ISO 3166-1 alpha-2)."""
    r = recommend(client, "BRA", "BRL", 100.0)
    assert r.status_code == 422


def test_country_too_short_returns_422(client):
    r = recommend(client, "B", "BRL", 100.0)
    assert r.status_code == 422


def test_currency_too_long_returns_422(client):
    """Currency must be exactly 3 characters (ISO 4217)."""
    r = recommend(client, "BR", "BRLL", 100.0)
    assert r.status_code == 422


def test_currency_too_short_returns_422(client):
    r = recommend(client, "BR", "BR", 100.0)
    assert r.status_code == 422


def test_amount_zero_returns_422(client):
    """Amount must be strictly greater than zero."""
    r = recommend(client, "BR", "BRL", 0)
    assert r.status_code == 422


def test_amount_negative_returns_422(client):
    r = recommend(client, "BR", "BRL", -50.0)
    assert r.status_code == 422


def test_amount_string_returns_422(client):
    r = client.post("/api/v1/recommendations",
                    json={"country": "BR", "currency": "BRL", "amount": "lots"})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Amount factor — out-of-range amounts penalise methods
# ---------------------------------------------------------------------------

def test_very_large_amount_penalises_gcash(client):
    """
    GCash has a $500 USD ceiling. PHP 1,000,000 ≈ $17,000 USD —
    far above the limit, so gcash score should be penalised and
    may no longer rank first.
    """
    r = recommend(client, "PH", "PHP", 1_000_000.0)
    assert r.status_code == 200
    # Score should still be returned but penalised
    recs = {rec["method"]: rec for rec in r.json()["recommendations"]}
    assert recs["gcash"]["score"] < recs["gcash"]["estimated_success_rate"]


def test_tiny_amount_below_oxxo_minimum(client):
    """
    OXXO minimum is $5 USD. MXN 1 ≈ $0.058 USD — well below the floor,
    so oxxo gets a penalty and its score < estimated_success_rate.
    """
    r = recommend(client, "MX", "MXN", 1.0)
    assert r.status_code == 200
    recs = {rec["method"]: rec for rec in r.json()["recommendations"]}
    assert recs["oxxo"]["score"] < recs["oxxo"]["estimated_success_rate"]


# ---------------------------------------------------------------------------
# Unknown currency code
# ---------------------------------------------------------------------------

def test_usd_accepted_for_all_countries(client):
    """USD is accepted as an alternative currency for every supported country."""
    for country in ("BR", "MX", "PH", "CO", "JP"):
        r = recommend(client, country, "USD", 100.0)
        assert r.status_code == 200, f"Expected 200 for {country}/USD, got {r.status_code}"


def test_wrong_currency_for_country_returns_422(client):
    """MXN is not a valid currency for Brazil."""
    r = recommend(client, "BR", "MXN", 150.0)
    assert r.status_code == 422


def test_wrong_currency_error_message_is_informative(client):
    """Error message should name the rejected currency and list accepted ones."""
    r = recommend(client, "BR", "MXN", 150.0)
    detail = r.json()["detail"]
    assert "MXN" in detail
    assert "BRL" in detail or "USD" in detail


def test_unknown_currency_code_returns_422(client):
    """'XXX' is not accepted for any country — returns 422 not a silent fallback."""
    r = recommend(client, "BR", "XXX", 150.0)
    assert r.status_code == 422
