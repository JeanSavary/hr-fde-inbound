from typing import Optional

from pydantic import BaseModel, Field


class FMCSACarrier(BaseModel):
    mc_number: str
    dot_number: str = ""
    legal_name: str
    dba_name: str = ""
    status: str
    authority_status: str  # "A" = Active, "I" = Inactive, "N" = None
    entity_type: str = ""
    safety_rating: str = ""
    out_of_service: bool = False
    phone: str = ""
    physical_address: str = ""
    # Insurance (values are in thousands of USD)
    bipd_insurance_on_file: int = 0
    bipd_required_amount: int = 0
    # Fleet info
    total_power_units: int = 0
    total_drivers: int = 0
    # Safety signals
    crash_total: int = 0
    driver_oos_rate: float = 0.0
    driver_oos_rate_national_avg: float = 5.51
    mcs150_outdated: bool = False
    oos_date: Optional[str] = None


class CarrierVerifyRequest(BaseModel):
    mc_number: str


class CarrierVerifyResponse(BaseModel):
    eligible: bool
    mc_number: str
    carrier_name: str = ""
    reasons: list[str] = Field(default_factory=list)


class CarrierInteractionRequest(BaseModel):
    mc_number: str
    carrier_name: Optional[str] = None
    call_id: Optional[str] = None
    call_length_seconds: Optional[int] = None
    outcome: Optional[str] = None
    load_id: Optional[str] = None
    notes: str = ""


class CarrierInteractionResponse(BaseModel):
    id: str
    mc_number: str
    carrier_name: Optional[str] = None
    call_id: Optional[str] = None
    call_length_seconds: Optional[int] = None
    outcome: Optional[str] = None
    load_id: Optional[str] = None
    notes: str
    created_at: str


class CarrierHistoryResponse(BaseModel):
    mc_number: str
    total_interactions: int
    interactions: list[CarrierInteractionResponse]
