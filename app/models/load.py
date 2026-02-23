from typing import Annotated, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.models.enums import EquipmentType
from app.models.location import ResolvedLocation

# Accepts int or a string that represents an integer (e.g. from a voice agent)
IntOrStr = Annotated[Optional[Union[int, str]], Field(default=None)]


def _to_int(v: Union[int, str, None]) -> Optional[int]:
    if v is None or v == "":
        return None
    return int(v)


class LaneSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin": "Dallas, TX",
                "destination": "Chicago, IL",
            }
        }
    )

    origin: str
    destination: str


class LoadSearchRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "origin": "Dallas",
                "equipment_type": "dry_van",
                "destination": "Houston",
                "pickup_datetime": "2026-02-22T08:00:00",
                "radius_miles": 75,
                "pickup_window_hours": 12,
                "max_distance_miles": 1000,
                "max_weight": 42000,
            }
        }
    )

    origin: str
    equipment_type: str = Field(
        ...,
        description="Equipment type. Values: dry_van, reefer, flatbed, "
        "step_deck, power_only",
    )
    destination: Optional[str] = Field(
        None, description="Destination city, state, or region"
    )
    pickup_datetime: Optional[str] = Field(
        None,
        description="Filter by pickup datetime (YYYY-MM-DDTHH:MM:SS)",
    )
    radius_miles: IntOrStr = Field(
        None, description="Search radius in miles (default 75)"
    )
    pickup_window_hours: IntOrStr = Field(
        None,
        description="Only loads picking up within this many hours from now",
    )
    max_distance_miles: IntOrStr = Field(
        None, description="Maximum haul distance in miles"
    )
    max_weight: IntOrStr = Field(
        None, description="Maximum load weight in lbs"
    )

    @field_validator(
        "radius_miles",
        "pickup_window_hours",
        "max_distance_miles",
        "max_weight",
        mode="before",
    )
    @classmethod
    def coerce_int(cls, v):
        return _to_int(v)

    @field_validator("equipment_type", mode="before")
    @classmethod
    def normalise_equipment(cls, v):
        if isinstance(v, str):
            return v.lower().strip().replace(" ", "_").replace("-", "_")
        return v


class Load(BaseModel):
    load_id: str
    origin: str
    origin_lat: float
    origin_lng: float
    destination: str
    dest_lat: float
    dest_lng: float
    pickup_datetime: str
    delivery_datetime: str
    equipment_type: EquipmentType
    loadboard_rate: float
    notes: str = ""
    weight: int
    commodity_type: str
    num_of_pieces: int = 0
    miles: int
    dimensions: str = ""


class SearchResultLoad(Load):
    """Load enriched with search-context metrics."""

    rate_per_mile: float
    deadhead_miles: float
    deadend_miles: float
    floor_rate: float
    max_rate: float


class AlternativeLoad(SearchResultLoad):
    """
    A load that didn't pass all strict filters but is close enough to pitch.
    `differences` lists every way it diverges from the carrier's request —
    ready to be read verbatim by the AI agent.
    """

    differences: list[str]


class PickupRescheduleRequest(BaseModel):
    load_id: str
    new_pickup_datetime: Optional[str] = Field(
        None,
        description="Requested new pickup datetime (ISO 8601)",
    )
    new_pickup_window: IntOrStr = Field(
        None,
        description="Pickup window in hours from now",
    )

    @field_validator("new_pickup_window", mode="before")
    @classmethod
    def coerce_window(cls, v):
        return _to_int(v)

    @model_validator(mode="after")
    def at_least_one(self):
        if (
            self.new_pickup_datetime is None
            and self.new_pickup_window is None
        ):
            raise ValueError(
                "Provide new_pickup_datetime or new_pickup_window"
            )
        return self


class PickupRescheduleResponse(BaseModel):
    load_id: str
    approved: bool
    current_pickup_datetime: str
    requested_pickup_datetime: str
    difference_hours: float
    reason: str


class LoadSearchResponse(BaseModel):
    loads: list[SearchResultLoad]
    alternative_loads: list[AlternativeLoad] = []
    origin_resolved: ResolvedLocation
    destination_resolved: ResolvedLocation | None
    radius_miles: int
    total_found: int
    total_alternatives: int = 0


class LoadWithStatus(Load):
    status: str = "available"
    booked_at: Optional[str] = None
    created_at: Optional[str] = None
    urgency: str = "normal"
    pitch_count: int = 0
    days_listed: int = 0
    rate_per_mile: Optional[float] = None


class LoadListResponse(BaseModel):
    loads: list[LoadWithStatus]
    total: int
    page: int
    page_size: int
