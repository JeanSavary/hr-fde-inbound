from enum import Enum
from typing import Optional

from pydantic import BaseModel


class LocationType(str, Enum):
    CITY = "city"
    STATE = "state"
    REGION = "region"


class ResolvedLocation(BaseModel):
    type: LocationType
    label: str
    lat: Optional[float] = None
    lng: Optional[float] = None

    @property
    def is_city(self) -> bool:
        return self.type == LocationType.CITY

    @property
    def is_state(self) -> bool:
        return self.type == LocationType.STATE

    @property
    def is_region(self) -> bool:
        return self.type == LocationType.REGION

    @staticmethod
    def city(
        name: str, lat: float, lng: float
    ) -> "ResolvedLocation":
        return ResolvedLocation(
            type=LocationType.CITY,
            label=name,
            lat=lat,
            lng=lng,
        )

    @staticmethod
    def state(abbrev: str) -> "ResolvedLocation":
        return ResolvedLocation(
            type=LocationType.STATE, label=abbrev
        )

    @staticmethod
    def region(name: str) -> "ResolvedLocation":
        return ResolvedLocation(
            type=LocationType.REGION, label=name
        )
