from typing import Optional, Union
from pydantic import BaseModel, field_validator
from app.models.enums import CallOutcome, Sentiment


class CallLogRequest(BaseModel):
    call_id: str
    mc_number: Optional[Union[str, int]] = None

    @field_validator("mc_number", mode="before")
    @classmethod
    def coerce_mc_to_str(cls, v):
        if v is not None:
            return str(v)
        return v
    carrier_name: Optional[str] = None
    lane_origin: Optional[str] = None
    lane_destination: Optional[str] = None
    equipment_type: Optional[str] = None
    load_id: Optional[str] = None
    initial_rate: Optional[float] = None
    final_rate: Optional[float] = None
    negotiation_rounds: int = 0
    carrier_phone: Optional[str] = None
    special_requests: Optional[str] = None
    outcome: CallOutcome
    sentiment: Sentiment
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[list[str]] = None


class CallLogResponse(BaseModel):
    id: str
    call_id: str
    outcome: str
    sentiment: str
    created_at: str


class CallDetailResponse(BaseModel):
    id: str
    call_id: str
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None
    lane_origin: Optional[str] = None
    lane_destination: Optional[str] = None
    equipment_type: Optional[str] = None
    load_id: Optional[str] = None
    initial_rate: Optional[float] = None
    final_rate: Optional[float] = None
    negotiation_rounds: int = 0
    carrier_phone: Optional[str] = None
    special_requests: Optional[str] = None
    outcome: str
    sentiment: str
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    key_points: Optional[list[str]] = None
    created_at: str


class CallListResponse(BaseModel):
    calls: list[CallDetailResponse]
    total: int
    page: int
    page_size: int
    kpi_total_calls: int = 0
    kpi_booking_rate: float = 0
    kpi_avg_duration: int = 0
    kpi_total_duration: int = 0
