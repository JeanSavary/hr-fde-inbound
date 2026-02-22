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


@router.get(
    "",
    response_model=NegotiationSettingsResponse,
    dependencies=[Security(verify_api_key)],
)
async def get_negotiation_settings():
    """Get current negotiation margin settings."""
    return NegotiationSettingsResponse(**get_all_settings())


@router.put(
    "",
    response_model=NegotiationSettingsResponse,
    dependencies=[Security(verify_api_key)],
)
async def update_negotiation_settings(
    body: NegotiationSettingsUpdate,
):
    """Update negotiation margin settings. Only provided fields are changed."""
    updates = {
        k: v
        for k, v in body.model_dump().items()
        if v is not None
    }
    if updates:
        upsert_all(updates)
    return NegotiationSettingsResponse(**get_all_settings())
