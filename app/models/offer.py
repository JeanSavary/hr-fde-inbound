from typing import Optional
from pydantic import BaseModel
from app.models.enums import OfferType, OfferStatus


class OfferCreateRequest(BaseModel):
    call_id: Optional[str] = None
    load_id: str
    mc_number: str
    offer_amount: float
    offer_type: OfferType
    round_number: int = 1
    status: OfferStatus = OfferStatus.PENDING
    notes: str = ""


class OfferResponse(BaseModel):
    offer_id: str
    call_id: Optional[str] = None
    load_id: str
    mc_number: str
    offer_amount: float
    offer_type: OfferType
    round_number: int
    status: OfferStatus
    notes: str
    created_at: str
    rate_floor: float
    rate_ceiling: float
