from fastapi import APIRouter, HTTPException, Security
from app.models.offer import (
    OfferCreateRequest,
    OfferResponse,
    OfferAnalysisRequest,
    OfferAnalysisResponse,
)
from app.services.offer_service import create_offer, analyze_offer
from app.db.repositories.negotiation_settings_repo import get_all_settings
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
    ns = get_all_settings()
    target_margin = ns.get("target_margin", 0.15)
    max_bump = ns.get("max_bump_above_loadboard", 0.03)
    response, error = create_offer(req, 1 - target_margin, 1 + max_bump)
    if error:
        raise HTTPException(404, error)
    return response


@router.post(
    "/analyze",
    response_model=OfferAnalysisResponse,
    dependencies=[Security(verify_api_key)],
)
async def analyze_offer_route(req: OfferAnalysisRequest):
    """
    Analyze a carrier's ask against a specific load.
    Returns accept, counter (with counter_offers list),
    or reject (with reason).
    """
    ns = get_all_settings()
    target_margin = ns.get("target_margin", 0.15)
    max_bump = ns.get("max_bump_above_loadboard", 0.03)
    result, error = analyze_offer(req, 1 - target_margin, 1 + max_bump)
    if error:
        status = 409 if "already booked" in error else 404
        raise HTTPException(status, error)
    return result
