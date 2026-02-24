from typing import Optional

from fastapi import HTTPException

from app.models.call import (
    CallLogRequest,
    CallLogResponse,
    CallDetailResponse,
    CallListResponse,
)
from app.db.repositories.call_repo import (
    insert_call,
    get_call_by_call_id,
    get_all_calls,
    get_calls_kpis,
)
from app.utils.period import period_since
from app.db.repositories.carrier_repo import insert_interaction


def log_call(req: CallLogRequest) -> CallLogResponse:
    call_data = req.model_dump()
    call_data["outcome"] = req.outcome.value
    call_data["sentiment"] = req.sentiment.value
    result = insert_call(call_data)

    # Cascade: create carrier interaction record
    if req.mc_number:
        insert_interaction(
            {
                "mc_number": str(req.mc_number),
                "carrier_name": req.carrier_name,
                "call_id": result["call_id"],
                "call_length_seconds": req.duration_seconds or 0,
                "outcome": result["outcome"],
                "load_id": req.load_id,
                "notes": "",
            }
        )

    # Booking is handled separately via POST /api/booked-loads
    # (triggered by the HappyRobot platform after the call)

    return CallLogResponse(
        id=result["id"],
        call_id=result["call_id"],
        outcome=result["outcome"],
        sentiment=result["sentiment"],
        created_at=result["created_at"],
    )


def get_call(call_id: str) -> CallDetailResponse:
    row = get_call_by_call_id(call_id)
    if row is None:
        raise HTTPException(
            status_code=404, detail=f"Call {call_id} not found"
        )
    return CallDetailResponse(**row)


def list_calls(
    outcome: Optional[str] = None,
    sentiment: Optional[str] = None,
    mc_number: Optional[str] = None,
    period: str = "last_month",
    page: int = 1,
    page_size: int = 50,
) -> CallListResponse:
    since = period_since(period)
    rows, total = get_all_calls(
        outcome=outcome,
        sentiment=sentiment,
        mc_number=mc_number,
        since=since,
        page=page,
        page_size=page_size,
    )
    kpis = get_calls_kpis(since)
    return CallListResponse(
        calls=[CallDetailResponse(**r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        **kpis,
    )
