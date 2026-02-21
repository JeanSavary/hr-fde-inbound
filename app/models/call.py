from typing import Optional
from pydantic import BaseModel
from app.models.enums import CallOutcome, Sentiment


class CallLogRequest(BaseModel):
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
    outcome: CallOutcome
    sentiment: Sentiment
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None


class CallLogResponse(BaseModel):
    id: str
    call_id: str
    outcome: str
    sentiment: str
    created_at: str
