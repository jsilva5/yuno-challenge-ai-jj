import sqlite3
import os
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "routeflow.db")


def init_db():
    """Initialize the SQLite database and create tables."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            country TEXT NOT NULL,
            currency TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL,
            success INTEGER NOT NULL,
            timestamp DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_transactions_country_method
            ON transactions(country, payment_method);
        CREATE INDEX IF NOT EXISTS idx_transactions_timestamp
            ON transactions(timestamp);
    """)
    conn.commit()
    conn.close()


def get_db():
    """Return a SQLite connection with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db_connection():
    """Context manager for database connections."""
    conn = get_db()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
