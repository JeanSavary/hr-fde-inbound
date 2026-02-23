from typing import Optional
from pydantic import BaseModel


class FunnelStage(BaseModel):
    stage: str
    count: int
    pct: float


class RateIntelligence(BaseModel):
    avg_loadboard: Optional[float] = None
    avg_agreed: Optional[float] = None
    discount_pct: Optional[float] = None
    margin_pct: Optional[float] = None


class DashboardMetrics(BaseModel):
    period: str = "today"
    total_calls: int
    avg_duration_seconds: Optional[float]
    calls_by_outcome: dict[str, int]
    sentiment_distribution: dict[str, int]
    booking_rate_percent: float
    avg_negotiation_rounds: Optional[float]
    avg_rate_differential_percent: Optional[float]
    total_revenue: float
    unique_carriers: int
    top_lanes: list[dict]
    equipment_demand: dict[str, int]
    recent_calls: list[dict]
    recent_offers: list[dict]

    # Period KPIs
    calls_today: int = 0
    calls_trend: Optional[str] = None
    booked_today: int = 0
    booked_trend: Optional[str] = None
    revenue_today: float = 0
    revenue_trend: Optional[str] = None
    conversion_rate: float = 0
    conversion_trend: Optional[str] = None
    pending_transfer: int = 0

    # Funnel
    funnel_data: list[FunnelStage] = []

    # Rate intelligence
    rate_intelligence: Optional[RateIntelligence] = None
