from fastapi import APIRouter, HTTPException, Security
from app.models.offer import OfferCreateRequest, OfferResponse
from app.services.offer_service import create_offer
from app.config import get_settings
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/offers", tags=["Offers"])


@router.post(
    "",
    response_model=OfferResponse,
    dependencies=[Security(verify_api_key)],
    include_in_schema=False,
)
async def create_offer_route(req: OfferCreateRequest):
    """Log negotiation offer. Returns rate floor/ceiling for agent."""
    s = get_settings()
    response, error = create_offer(
        req, s.rate_floor_percent, s.rate_ceiling_percent
    )
    if error:
        raise HTTPException(404, error)
    return response
