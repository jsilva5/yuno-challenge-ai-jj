"""
Shared fixtures for all test modules.

Uses an in-memory SQLite database so tests are fully isolated from
the production routeflow.db file.
"""

import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_db_conn


def make_db() -> sqlite3.Connection:
    """Create an isolated in-memory SQLite DB with the app schema."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE transactions (
            id TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            currency TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            success INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_transactions_country_method
            ON transactions(country, payment_method);
        CREATE INDEX idx_transactions_timestamp
            ON transactions(timestamp);
    """)
    conn.commit()
    return conn


@pytest.fixture
def db():
    """Fresh in-memory database per test — no shared state between tests."""
    conn = make_db()
    yield conn
    conn.close()


@pytest.fixture
def client(db):
    """TestClient wired to the in-memory database."""
    def override():
        yield db

    app.dependency_overrides[get_db_conn] = override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def seed_transaction(db, country, currency, amount, method, success,
                     timestamp="2024-06-15 12:00:00"):
    """Insert a single transaction directly into the test DB."""
    db.execute(
        """INSERT INTO transactions
           (id, country, currency, amount, payment_method, success, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid.uuid4()), country, currency, amount, method,
         1 if success else 0, timestamp),
    )
    db.commit()
