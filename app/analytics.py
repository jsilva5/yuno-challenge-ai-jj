from typing import List, Optional
from app.models import AnalyticsMetric


def get_analytics_metrics(
    conn,
    country: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> List[AnalyticsMetric]:
    """Aggregate transaction metrics with optional filters."""
    query = """
        SELECT
            country,
            payment_method,
            COUNT(*) AS total_attempts,
            SUM(success) AS total_success,
            AVG(CAST(success AS REAL)) AS success_rate,
            AVG(amount) AS avg_amount
        FROM transactions
        WHERE 1=1
    """
    params = []

    if country:
        query += " AND country = ?"
        params.append(country)
    if from_date:
        query += " AND DATE(timestamp) >= ?"
        params.append(from_date)
    if to_date:
        query += " AND DATE(timestamp) <= ?"
        params.append(to_date)

    query += " GROUP BY country, payment_method ORDER BY country, success_rate DESC"

    rows = conn.execute(query, params).fetchall()

    return [
        AnalyticsMetric(
            country=row["country"],
            payment_method=row["payment_method"],
            total_attempts=row["total_attempts"],
            total_success=int(row["total_success"] or 0),
            success_rate=round(float(row["success_rate"] or 0), 4),
            avg_amount=round(float(row["avg_amount"] or 0), 2),
        )
        for row in rows
    ]
