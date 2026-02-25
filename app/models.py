from pydantic import BaseModel, Field
from typing import List, Optional
from typing import Literal
from datetime import datetime

CountryCode = Literal["BR", "MX", "PH", "CO", "JP"]
CurrencyCode = Literal["BRL", "MXN", "PHP", "COP", "JPY", "USD"]
PaymentMethod = Literal[
    "pix", "boleto", "credit_card",          # BR
    "oxxo", "spei",                           # MX
    "gcash", "grabpay",                       # PH
    "pse", "neki",                            # CO
    "paypay", "seven_eleven",                 # JP
]


class RecommendationRequest(BaseModel):
    country: CountryCode = Field(..., description="Supported country code: BR, MX, PH, CO, JP")
    currency: CurrencyCode = Field(
        ...,
        description=(
            "Currency for the transaction. Each country accepts its native currency or USD. "
            "BR→BRL, MX→MXN, PH→PHP, CO→COP, JP→JPY. USD is accepted for all countries."
        ),
    )
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
    country: CountryCode = Field(..., description="Supported country code: BR, MX, PH, CO, JP")
    currency: CurrencyCode = Field(
        ...,
        description="Native currency for the country, or USD. BR→BRL, MX→MXN, PH→PHP, CO→COP, JP→JPY.",
    )
    amount: float = Field(..., gt=0, description="Transaction amount in the given currency")
    payment_method: PaymentMethod = Field(..., description="Payment method used for the transaction")
    success: bool = Field(..., description="Whether the transaction succeeded")
    timestamp: Optional[datetime] = Field(None, description="Transaction time (defaults to now if omitted)")


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
