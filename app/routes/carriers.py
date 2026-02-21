from fastapi import APIRouter, Security
from app.config import get_settings
from app.models.carrier import CarrierVerifyRequest, CarrierVerifyResponse
from app.services.carrier_service import verify_carrier
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/carriers", tags=["Carriers"])


@router.post(
    "/verify",
    response_model=CarrierVerifyResponse,
    dependencies=[Security(verify_api_key)],
)
async def verify_carrier_route(req: CarrierVerifyRequest):
    """Check carrier eligibility: active authority, not OOS, safe rating."""
    return await verify_carrier(req.mc_number, get_settings().fmcsa_web_key)
