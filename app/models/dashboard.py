from typing import Optional
from pydantic import BaseModel


class DashboardMetrics(BaseModel):
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
