"""
Tests for GET /api/v1/health
"""


def test_health_returns_200(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_health_status_is_ok(client):
    data = client.get("/api/v1/health").json()
    assert data["status"] == "ok"


def test_health_db_status_is_ok(client):
    data = client.get("/api/v1/health").json()
    assert data["db_status"] == "ok"


def test_health_version_present(client):
    data = client.get("/api/v1/health").json()
    assert "version" in data
    assert data["version"] != ""


def test_health_response_has_all_fields(client):
    data = client.get("/api/v1/health").json()
    assert set(data.keys()) == {"status", "version", "db_status"}
