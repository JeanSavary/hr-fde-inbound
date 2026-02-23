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
    max_negotiation_rounds: int = Field(
        3, description="Maximum number of negotiation rounds per call"
    )
    max_offers_per_call: int = Field(
        3, description="Maximum number of offers per call"
    )
    auto_transfer_threshold: int = Field(
        500, description="Dollar threshold for automatic transfer to human"
    )
    deadhead_warning_miles: int = Field(
        150, description="Miles threshold for deadhead warning"
    )
    floor_rate_protection: bool = Field(
        True, description="Enable floor rate protection"
    )
    sentiment_escalation: bool = Field(
        True, description="Enable sentiment-based escalation"
    )
    prioritize_perishables: bool = Field(
        True, description="Prioritize perishable loads"
    )
    agent_greeting: str = Field(
        "Thanks for calling, this is your AI carrier sales agent. How can I help you today?",
        description="Greeting message used by the AI agent",
    )
    agent_tone: str = Field(
        "professional", description="Tone of the AI agent (e.g. professional, friendly)"
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
    max_negotiation_rounds: Optional[int] = Field(
        None, description="Maximum number of negotiation rounds per call"
    )
    max_offers_per_call: Optional[int] = Field(
        None, description="Maximum number of offers per call"
    )
    auto_transfer_threshold: Optional[int] = Field(
        None, description="Dollar threshold for automatic transfer to human"
    )
    deadhead_warning_miles: Optional[int] = Field(
        None, description="Miles threshold for deadhead warning"
    )
    floor_rate_protection: Optional[bool] = Field(
        None, description="Enable floor rate protection"
    )
    sentiment_escalation: Optional[bool] = Field(
        None, description="Enable sentiment-based escalation"
    )
    prioritize_perishables: Optional[bool] = Field(
        None, description="Prioritize perishable loads"
    )
    agent_greeting: Optional[str] = Field(
        None, description="Greeting message used by the AI agent"
    )
    agent_tone: Optional[str] = Field(
        None, description="Tone of the AI agent (e.g. professional, friendly)"
    )
