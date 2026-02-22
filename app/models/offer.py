from typing import Optional, Union
from pydantic import BaseModel, field_validator, model_validator
from app.models.enums import OfferType, OfferStatus, Verdict


class OfferAnalysisRequest(BaseModel):
    load_id: str
    asking_rate: Optional[float] = None
    asking_pickup_datetime: Optional[str] = None
    asking_pickup_window_hours: Optional[int] = None
    asking_radius_miles: Optional[int] = None

    @model_validator(mode="after")
    def at_least_one_param(self):
        optional = [
            self.asking_rate,
            self.asking_pickup_datetime,
            self.asking_pickup_window_hours,
            self.asking_radius_miles,
        ]
        if not any(v is not None for v in optional):
            raise ValueError(
                "At least one optional parameter must be provided"
            )
        return self


class OfferAnalysisResponse(BaseModel):
    load_id: str
    verdict: Verdict
    reason: Optional[str] = None
    counter_offers: Optional[list[str]] = None


class BookedLoadRequest(BaseModel):
    load_id: str
    mc_number: Union[str, int]
    carrier_name: Optional[str] = None
    agreed_rate: Optional[float] = None
    agreed_pickup_datetime: Optional[str] = None
    call_id: str

    @field_validator("mc_number", mode="before")
    @classmethod
    def coerce_mc(cls, v):
        return str(v)


class BookedLoadResponse(BaseModel):
    success: bool = True
    id: str
    load_id: str
    mc_number: str
    carrier_name: Optional[str] = None
    agreed_rate: float
    agreed_pickup_datetime: Optional[str] = None
    offer_id: Optional[str] = None
    call_id: Optional[str] = None
    created_at: str


class OfferCreateRequest(BaseModel):
    call_id: Optional[str] = None
    load_id: str
    mc_number: str
    offer_amount: float
    offer_type: OfferType
    round_number: int = 1
    status: OfferStatus = OfferStatus.PENDING
    notes: str = ""
    agreed_pickup_datetime: Optional[str] = None


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
    original_rate: float
    rate_difference: float
    rate_difference_pct: float
    original_pickup_datetime: str
    agreed_pickup_datetime: Optional[str] = None
    pickup_changed: bool = False
