from typing import Optional

from pydantic import BaseModel, Field


class NegotiationSettingsResponse(BaseModel):
    target_margin: float = Field(
        ..., description="Target gross margin (e.g. 0.15 = 15%)"
    )
    min_margin: float = Field(
        ..., description="Minimum acceptable margin (e.g. 0.05 = 5%)"
    )
    max_bump_above_loadboard: float = Field(
        ...,
        description="Max rate bump above loadboard (e.g. 0.03 = 3%)",
    )


class NegotiationSettingsUpdate(BaseModel):
    target_margin: Optional[float] = Field(
        None, description="Target gross margin (e.g. 0.15 = 15%)"
    )
    min_margin: Optional[float] = Field(
        None, description="Minimum acceptable margin (e.g. 0.05 = 5%)"
    )
    max_bump_above_loadboard: Optional[float] = Field(
        None,
        description="Max rate bump above loadboard (e.g. 0.03 = 3%)",
    )
