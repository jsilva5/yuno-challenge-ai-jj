"""
Tests for GET /api/v1/analytics

Covers:
- Empty database returns empty metrics (not an error)
- No filters returns all data across countries
- Filter by country
- Filter by date range (from_date, to_date, both)
- Unknown country filter returns empty (not 404)
- Inverted date range returns empty
- Correct success_rate and avg_amount calculations
- Response structure
"""

import pytest
from tests.conftest import seed_transaction


# ---------------------------------------------------------------------------
# Empty database
# ---------------------------------------------------------------------------

def test_empty_db_returns_200(client):
    r = client.get("/api/v1/analytics")
    assert r.status_code == 200


def test_empty_db_returns_empty_metrics(client):
    data = client.get("/api/v1/analytics").json()
    assert data["metrics"] == []


def test_empty_db_has_empty_filters(client):
    data = client.get("/api/v1/analytics").json()
    assert data["filters"] == {}


# ---------------------------------------------------------------------------
# No filters — returns everything
# ---------------------------------------------------------------------------

def test_no_filter_returns_all_countries(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)
    seed_transaction(db, "MX", "MXN", 200.0, "oxxo", False)

    data = client.get("/api/v1/analytics").json()
    countries = {m["country"] for m in data["metrics"]}
    assert "BR" in countries
    assert "MX" in countries


def test_response_structure(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)

    data = client.get("/api/v1/analytics").json()
    assert "filters" in data
    assert "metrics" in data

    metric = data["metrics"][0]
    for field in ("country", "payment_method", "total_attempts",
                  "total_success", "success_rate", "avg_amount"):
        assert field in metric


# ---------------------------------------------------------------------------
# Country filter
# ---------------------------------------------------------------------------

def test_country_filter_returns_only_that_country(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)
    seed_transaction(db, "MX", "MXN", 200.0, "oxxo", True)

    data = client.get("/api/v1/analytics?country=BR").json()
    countries = {m["country"] for m in data["metrics"]}
    assert countries == {"BR"}


def test_country_filter_appears_in_filters_field(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)

    data = client.get("/api/v1/analytics?country=BR").json()
    assert data["filters"]["country"] == "BR"


def test_country_filter_lowercase_is_normalised(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)

    data = client.get("/api/v1/analytics?country=br").json()
    assert len(data["metrics"]) == 1
    assert data["metrics"][0]["country"] == "BR"


def test_unknown_country_filter_returns_empty_metrics(client, db):
    """Filtering by a country with no data should return [] not a 404."""
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)

    data = client.get("/api/v1/analytics?country=ZZ").json()
    assert data["metrics"] == []


def test_country_not_in_config_filter_returns_empty(client, db):
    """
    'US' is not in COUNTRY_METHODS but if someone recorded transactions
    for it, they'd appear. With no data, it returns empty.
    """
    data = client.get("/api/v1/analytics?country=US").json()
    assert data["metrics"] == []


# ---------------------------------------------------------------------------
# Metrics correctness
# ---------------------------------------------------------------------------

def test_success_rate_calculation(client, db):
    """3 attempts, 2 successes → success_rate = 0.6667"""
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)
    seed_transaction(db, "BR", "BRL", 100.0, "pix", False)

    data = client.get("/api/v1/analytics?country=BR").json()
    pix = next(m for m in data["metrics"] if m["payment_method"] == "pix")
    assert pix["total_attempts"] == 3
    assert pix["total_success"] == 2
    assert abs(pix["success_rate"] - 2 / 3) < 0.001


def test_avg_amount_calculation(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)
    seed_transaction(db, "BR", "BRL", 200.0, "pix", True)

    data = client.get("/api/v1/analytics?country=BR").json()
    pix = next(m for m in data["metrics"] if m["payment_method"] == "pix")
    assert abs(pix["avg_amount"] - 150.0) < 0.01


def test_zero_successes_success_rate_is_zero(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "credit_card", False)
    seed_transaction(db, "BR", "BRL", 100.0, "credit_card", False)

    data = client.get("/api/v1/analytics?country=BR").json()
    cc = next(m for m in data["metrics"] if m["payment_method"] == "credit_card")
    assert cc["success_rate"] == 0.0
    assert cc["total_success"] == 0


def test_multiple_methods_per_country(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True)
    seed_transaction(db, "BR", "BRL", 200.0, "credit_card", False)

    data = client.get("/api/v1/analytics?country=BR").json()
    methods = {m["payment_method"] for m in data["metrics"]}
    assert "pix" in methods
    assert "credit_card" in methods


# ---------------------------------------------------------------------------
# Date range filters
# ---------------------------------------------------------------------------

def test_from_date_filter_excludes_older_transactions(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2023-01-15 12:00:00")
    seed_transaction(db, "BR", "BRL", 200.0, "pix", True,
                     timestamp="2024-06-15 12:00:00")

    data = client.get("/api/v1/analytics?country=BR&from_date=2024-01-01").json()
    pix = next(m for m in data["metrics"] if m["payment_method"] == "pix")
    assert pix["total_attempts"] == 1


def test_to_date_filter_excludes_newer_transactions(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2023-01-15 12:00:00")
    seed_transaction(db, "BR", "BRL", 200.0, "pix", True,
                     timestamp="2024-06-15 12:00:00")

    data = client.get("/api/v1/analytics?country=BR&to_date=2023-12-31").json()
    pix = next(m for m in data["metrics"] if m["payment_method"] == "pix")
    assert pix["total_attempts"] == 1


def test_date_range_both_bounds(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2022-06-01 12:00:00")
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2023-06-01 12:00:00")
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2024-06-01 12:00:00")

    data = client.get(
        "/api/v1/analytics?country=BR&from_date=2023-01-01&to_date=2023-12-31"
    ).json()
    pix = next(m for m in data["metrics"] if m["payment_method"] == "pix")
    assert pix["total_attempts"] == 1


def test_inverted_date_range_returns_empty(client, db):
    """from_date after to_date should match nothing."""
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2024-06-15 12:00:00")

    data = client.get(
        "/api/v1/analytics?from_date=2024-12-31&to_date=2024-01-01"
    ).json()
    assert data["metrics"] == []


def test_date_range_with_no_matching_transactions_returns_empty(client, db):
    seed_transaction(db, "BR", "BRL", 100.0, "pix", True,
                     timestamp="2024-06-15 12:00:00")

    data = client.get(
        "/api/v1/analytics?from_date=2020-01-01&to_date=2020-12-31"
    ).json()
    assert data["metrics"] == []


def test_date_filters_appear_in_filters_field(client, db):
    data = client.get(
        "/api/v1/analytics?from_date=2024-01-01&to_date=2024-12-31"
    ).json()
    assert data["filters"]["from_date"] == "2024-01-01"
    assert data["filters"]["to_date"] == "2024-12-31"
