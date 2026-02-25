"""
Tests for POST /api/v1/transactions

Covers:
- Recording successful and failed transactions
- UUID generation and uniqueness
- Country code normalisation
- Optional timestamp handling
- Accepting unknown countries and payment methods (no config validation)
- Input validation (422 errors)
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def record(client, country, currency, amount, method, success, **extra):
    payload = {
        "country": country,
        "currency": currency,
        "amount": amount,
        "payment_method": method,
        "success": success,
        **extra,
    }
    return client.post("/api/v1/transactions", json=payload)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_record_success_true_returns_200(client):
    r = record(client, "BR", "BRL", 150.0, "pix", True)
    assert r.status_code == 200


def test_record_success_false_returns_200(client):
    r = record(client, "BR", "BRL", 150.0, "credit_card", False)
    assert r.status_code == 200


def test_response_has_id_and_status(client):
    data = record(client, "MX", "MXN", 500.0, "oxxo", True).json()
    assert "id" in data
    assert data["status"] == "recorded"


def test_response_id_is_valid_uuid(client):
    import uuid
    data = record(client, "BR", "BRL", 100.0, "pix", True).json()
    # Should not raise
    uuid.UUID(data["id"])


def test_two_transactions_have_different_ids(client):
    id1 = record(client, "BR", "BRL", 100.0, "pix", True).json()["id"]
    id2 = record(client, "BR", "BRL", 100.0, "pix", True).json()["id"]
    assert id1 != id2


def test_transaction_with_explicit_timestamp(client):
    r = record(client, "BR", "BRL", 200.0, "pix", True,
               timestamp="2024-03-15T14:30:00")
    assert r.status_code == 200
    assert r.json()["status"] == "recorded"


def test_transaction_without_timestamp_uses_current_time(client):
    """Omitting timestamp should default to now — endpoint must still succeed."""
    r = record(client, "CO", "COP", 50_000.0, "pse", True)
    assert r.status_code == 200


def test_transaction_with_past_timestamp(client):
    r = record(client, "JP", "JPY", 3000.0, "paypay", True,
               timestamp="2020-01-01T00:00:00")
    assert r.status_code == 200


def test_transaction_with_future_timestamp(client):
    r = record(client, "PH", "PHP", 200.0, "gcash", False,
               timestamp="2099-12-31T23:59:59")
    assert r.status_code == 200


def test_country_lowercase_is_normalised(client):
    """Lowercase 'br' should be stored as 'BR' without error."""
    r = record(client, "br", "BRL", 100.0, "pix", True)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Unknown / unsupported values — should still record (no config validation)
# ---------------------------------------------------------------------------

def test_unknown_country_returns_404(client):
    """
    Both endpoints share the same country validation — unknown countries
    (not in COUNTRY_METHODS / COUNTRY_CURRENCIES) return 404.
    """
    r = record(client, "US", "USD", 99.0, "venmo", True)
    assert r.status_code == 404


def test_unknown_payment_method_still_records(client):
    """An unrecognised method name should be stored without error."""
    r = record(client, "BR", "BRL", 100.0, "nonexistent_wallet", False)
    assert r.status_code == 200


def test_unknown_currency_returns_422(client):
    """Currency is validated against accepted codes for the given country."""
    r = record(client, "BR", "XXX", 100.0, "pix", True)
    assert r.status_code == 422


def test_wrong_currency_for_country_returns_422(client):
    """MXN is valid format but not accepted for Brazil."""
    r = record(client, "BR", "MXN", 100.0, "pix", True)
    assert r.status_code == 422


def test_usd_accepted_for_all_countries_in_transactions(client):
    """USD is accepted as an alternative currency for every supported country."""
    for country, method in [("BR", "pix"), ("MX", "oxxo"), ("PH", "gcash"),
                             ("CO", "pse"), ("JP", "paypay")]:
        r = record(client, country, "USD", 100.0, method, True)
        assert r.status_code == 200, f"Expected 200 for {country}/USD, got {r.status_code}"


# ---------------------------------------------------------------------------
# Validation errors (422 Unprocessable Entity)
# ---------------------------------------------------------------------------

def test_missing_country_returns_422(client):
    r = client.post("/api/v1/transactions",
                    json={"currency": "BRL", "amount": 100.0,
                          "payment_method": "pix", "success": True})
    assert r.status_code == 422


def test_missing_currency_returns_422(client):
    r = client.post("/api/v1/transactions",
                    json={"country": "BR", "amount": 100.0,
                          "payment_method": "pix", "success": True})
    assert r.status_code == 422


def test_missing_amount_returns_422(client):
    r = client.post("/api/v1/transactions",
                    json={"country": "BR", "currency": "BRL",
                          "payment_method": "pix", "success": True})
    assert r.status_code == 422


def test_missing_payment_method_returns_422(client):
    r = client.post("/api/v1/transactions",
                    json={"country": "BR", "currency": "BRL",
                          "amount": 100.0, "success": True})
    assert r.status_code == 422


def test_missing_success_returns_422(client):
    r = client.post("/api/v1/transactions",
                    json={"country": "BR", "currency": "BRL",
                          "amount": 100.0, "payment_method": "pix"})
    assert r.status_code == 422


def test_amount_zero_returns_422(client):
    r = record(client, "BR", "BRL", 0, "pix", True)
    assert r.status_code == 422


def test_amount_negative_returns_422(client):
    r = record(client, "BR", "BRL", -1.0, "pix", True)
    assert r.status_code == 422


def test_country_too_long_returns_422(client):
    r = record(client, "BRA", "BRL", 100.0, "pix", True)
    assert r.status_code == 422


def test_country_too_short_returns_422(client):
    r = record(client, "B", "BRL", 100.0, "pix", True)
    assert r.status_code == 422


def test_currency_too_long_returns_422(client):
    r = record(client, "BR", "BRLL", 100.0, "pix", True)
    assert r.status_code == 422


def test_currency_too_short_returns_422(client):
    r = record(client, "BR", "BR", 100.0, "pix", True)
    assert r.status_code == 422


def test_invalid_timestamp_format_returns_422(client):
    r = record(client, "BR", "BRL", 100.0, "pix", True,
               timestamp="not-a-date")
    assert r.status_code == 422


def test_empty_body_returns_422(client):
    r = client.post("/api/v1/transactions", json={})
    assert r.status_code == 422
