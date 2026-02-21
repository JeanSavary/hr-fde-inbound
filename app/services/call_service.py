from app.models.call import CallLogRequest, CallLogResponse
from app.db.repositories.call_repo import insert_call


def log_call(req: CallLogRequest) -> CallLogResponse:
    call_data = req.model_dump()
    call_data["outcome"] = req.outcome.value
    call_data["sentiment"] = req.sentiment.value
    result = insert_call(call_data)
    return CallLogResponse(
        id=result["id"],
        call_id=result["call_id"],
        outcome=result["outcome"],
        sentiment=result["sentiment"],
        created_at=result["created_at"],
    )
