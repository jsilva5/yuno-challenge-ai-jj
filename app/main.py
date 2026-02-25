import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Query
import sqlite3

from app.database import init_db, get_db
from app.models import (
    RecommendationRequest,
    RecommendationResponse,
    TransactionRequest,
    TransactionResponse,
    AnalyticsResponse,
    HealthResponse,
)
from app.router import get_recommendations
from app.analytics import get_analytics_metrics
from app.config import COUNTRY_CURRENCIES

app = FastAPI(
    title="RouteFlow Payment Method Router",
    description=(
        "Intelligent payment method routing service that prioritizes methods "
        "by predicted success probability using Bayesian scoring on historical outcomes."
    ),
    version="1.0.0",
)


@app.on_event("startup")
def startup_event():
    init_db()


def get_db_conn():
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
def health_check(conn=Depends(get_db_conn)):
    try:
        conn.execute("SELECT 1").fetchone()
        db_status = "ok"
    except Exception:
        db_status = "error"
    return HealthResponse(status="ok", version="1.0.0", db_status=db_status)


def validate_country_currency(country: str, currency: str):
    accepted = COUNTRY_CURRENCIES.get(country)
    if accepted is None:
        raise HTTPException(status_code=404, detail=f"No payment methods configured for country '{country}'")
    if currency not in accepted:
        raise HTTPException(
            status_code=422,
            detail=f"Currency '{currency}' is not accepted for country '{country}'. Accepted: {sorted(accepted)}"
        )


@app.post(
    "/api/v1/recommendations",
    response_model=RecommendationResponse,
    tags=["Routing"],
    summary="Get ranked payment methods for a transaction",
    description=(
        "Returns payment methods available for the given country, ranked by predicted success probability "
        "using Bayesian scoring on historical transaction outcomes. "
        "Each country only accepts its native currency or USD."
    ),
    responses={
        404: {"description": "Country not supported"},
        422: {"description": "Currency not accepted for the given country"},
    },
)
def recommend_payment_methods(request: RecommendationRequest, conn=Depends(get_db_conn)):
    country = request.country.upper()
    currency = request.currency.upper()
    validate_country_currency(country, currency)
    recommendations = get_recommendations(country, currency, request.amount, conn)
    if not recommendations:
        raise HTTPException(
            status_code=404,
            detail=f"No payment methods configured for country '{country}'"
        )
    return RecommendationResponse(
        country=country,
        currency=currency,
        amount=request.amount,
        recommendations=recommendations,
    )


@app.post(
    "/api/v1/transactions",
    response_model=TransactionResponse,
    tags=["Transactions"],
    summary="Record a payment transaction outcome",
    description=(
        "Records the outcome of a payment attempt. Each recorded transaction feeds the Bayesian "
        "scoring model, so future recommendations for the same country and method will reflect "
        "the accumulated real-world success rates."
    ),
    responses={
        404: {"description": "Country not supported"},
        422: {"description": "Currency not accepted for the given country"},
    },
)
def record_transaction(request: TransactionRequest, conn=Depends(get_db_conn)):
    country = request.country.upper()
    currency = request.currency.upper()
    validate_country_currency(country, currency)
    transaction_id = str(uuid.uuid4())
    timestamp = request.timestamp or datetime.now(timezone.utc)

    try:
        conn.execute(
            """
            INSERT INTO transactions (id, country, currency, amount, payment_method, success, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                transaction_id,
                country,
                currency,
                request.amount,
                request.payment_method,
                1 if request.success else 0,
                timestamp.isoformat(),
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=f"Transaction recording failed: {str(e)}")

    return TransactionResponse(id=transaction_id, status="recorded")


@app.get("/api/v1/analytics", response_model=AnalyticsResponse, tags=["Analytics"])
def get_analytics(
    country: Optional[str] = Query(None, description="Filter by country code"),
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    conn=Depends(get_db_conn),
):
    country_upper = country.upper() if country else None
    metrics = get_analytics_metrics(conn, country=country_upper, from_date=from_date, to_date=to_date)
    filters = {}
    if country_upper:
        filters["country"] = country_upper
    if from_date:
        filters["from_date"] = from_date
    if to_date:
        filters["to_date"] = to_date
    return AnalyticsResponse(filters=filters, metrics=metrics)
