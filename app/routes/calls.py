from typing import Optional

from fastapi import APIRouter, Query, Security

from app.models.call import (
    CallLogRequest,
    CallLogResponse,
    CallDetailResponse,
    CallListResponse,
)
from app.services.call_service import log_call, get_call, list_calls
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.post(
    "",
    response_model=CallLogResponse,
    dependencies=[Security(verify_api_key)],
)
async def log_call_route(req: CallLogRequest):
    """Log post-call data: extracted info, outcome, sentiment."""
    return log_call(req)


@router.get(
    "",
    response_model=CallListResponse,
    dependencies=[Security(verify_api_key)],
)
async def list_calls_route(
    outcome: Optional[str] = Query(
        None, description="Filter by call outcome"
    ),
    sentiment: Optional[str] = Query(
        None, description="Filter by carrier sentiment"
    ),
    mc_number: Optional[str] = Query(None, description="Filter by carrier MC number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
):
    """List all calls with optional filtering and pagination."""
    return list_calls(
        outcome=outcome,
        sentiment=sentiment,
        mc_number=mc_number,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{call_id}",
    response_model=CallDetailResponse,
    dependencies=[Security(verify_api_key)],
)
async def get_call_route(call_id: str):
    """Get full details of a single call by its call_id."""
    return get_call(call_id)
