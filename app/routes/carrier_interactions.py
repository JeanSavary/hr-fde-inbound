from fastapi import APIRouter, Security

from app.models.carrier import (
    CarrierInteractionRequest,
    CarrierInteractionResponse,
    CarrierHistoryResponse,
)
from app.services.carrier_interaction_service import (
    log_interaction,
    get_carrier_history,
)
from app.routes._auth import verify_api_key

router = APIRouter(
    prefix="/api/carriers",
    tags=["Carrier Interactions"],
)


@router.post(
    "/interactions",
    response_model=CarrierInteractionResponse,
    dependencies=[Security(verify_api_key)],
)
async def log_carrier_interaction(req: CarrierInteractionRequest):
    """Log a carrier interaction (call, contact, etc.)."""
    return log_interaction(req)


@router.get(
    "/{mc_number}/interactions",
    response_model=CarrierHistoryResponse,
    dependencies=[Security(verify_api_key)],
)
async def get_carrier_interactions(mc_number: str):
    """Get full interaction history for a carrier by MC number."""
    return get_carrier_history(mc_number)
