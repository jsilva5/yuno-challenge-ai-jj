from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class RecommendationRequest(BaseModel):
    country: str = Field(..., min_length=2, max_length=2, description="ISO 3166-1 alpha-2 country code")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    amount: float = Field(..., gt=0, description="Transaction amount in the given currency")


class MethodRecommendation(BaseModel):
    method: str
    estimated_success_rate: float
    score: float
    data_points: int


class RecommendationResponse(BaseModel):
    country: str
    currency: str
    amount: float
    recommendations: List[MethodRecommendation]


class TransactionRequest(BaseModel):
    country: str = Field(..., min_length=2, max_length=2)
    currency: str = Field(..., min_length=3, max_length=3)
    amount: float = Field(..., gt=0)
    payment_method: str
    success: bool
    timestamp: Optional[datetime] = None


class TransactionResponse(BaseModel):
    id: str
    status: str


class AnalyticsMetric(BaseModel):
    country: str
    payment_method: str
    total_attempts: int
    total_success: int
    success_rate: float
    avg_amount: float


class AnalyticsResponse(BaseModel):
    filters: dict
    metrics: List[AnalyticsMetric]


class HealthResponse(BaseModel):
    status: str
    version: str
    db_status: str
