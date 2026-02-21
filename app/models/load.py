from pydantic import BaseModel

from app.models.enums import EquipmentType


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
    deadhead_miles: float       # empty miles to reach the pickup
    deadend_miles: float        # empty miles from delivery to desired destination


class AlternativeLoad(SearchResultLoad):
    """
    A load that didn't pass all strict filters but is close enough to pitch.
    `differences` lists every way it diverges from the carrier's request —
    ready to be read verbatim by the AI agent.
    """

    differences: list[str]


class LoadSearchResponse(BaseModel):
    loads: list[SearchResultLoad]
    alternative_loads: list[AlternativeLoad] = []
    origin_resolved: str
    destination_resolved: str | None
    radius_miles: int
    total_found: int
    total_alternatives: int = 0
