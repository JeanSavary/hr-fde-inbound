from fastapi import APIRouter, Security
from app.models.call import CallLogRequest, CallLogResponse
from app.services.call_service import log_call
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.post(
    "",
    response_model=CallLogResponse,
    dependencies=[Security(verify_api_key)],
    include_in_schema=False,
)
async def log_call_route(req: CallLogRequest):
    """Log post-call data: extracted info, outcome, sentiment."""
    return log_call(req)
