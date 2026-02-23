from fastapi import APIRouter, Security

from app.models.negotiation_settings import (
    NegotiationSettingsResponse,
    NegotiationSettingsUpdate,
)
from app.db.repositories.negotiation_settings_repo import (
    get_all_settings,
    upsert_all,
)
from app.routes._auth import verify_api_key

router = APIRouter(
    prefix="/api/settings/negotiation",
    tags=["Settings"],
)

_BOOL_FIELDS = {"floor_rate_protection", "sentiment_escalation", "prioritize_perishables"}
_INT_FIELDS = {
    "max_negotiation_rounds",
    "max_offers_per_call",
    "auto_transfer_threshold",
    "deadhead_warning_miles",
}


def _settings_from_db(raw: dict) -> dict:
    """Convert raw DB dict to proper Python types for the response model."""
    converted = {}
    for key, value in raw.items():
        if key in _BOOL_FIELDS:
            converted[key] = bool(value)
        elif key in _INT_FIELDS:
            converted[key] = int(value)
        else:
            converted[key] = value
    return converted


@router.get(
    "",
    response_model=NegotiationSettingsResponse,
    dependencies=[Security(verify_api_key)],
)
async def get_negotiation_settings():
    """Get current negotiation settings."""
    raw = get_all_settings()
    return NegotiationSettingsResponse(**_settings_from_db(raw))


@router.put(
    "",
    response_model=NegotiationSettingsResponse,
    dependencies=[Security(verify_api_key)],
)
async def update_negotiation_settings(
    body: NegotiationSettingsUpdate,
):
    """Update negotiation settings. Only provided fields are changed."""
    updates: dict[str, float | str | int] = {}
    for k, v in body.model_dump().items():
        if v is not None:
            if k in _BOOL_FIELDS:
                updates[k] = int(v)
            else:
                updates[k] = v
    if updates:
        upsert_all(updates)
    raw = get_all_settings()
    return NegotiationSettingsResponse(**_settings_from_db(raw))
