from app.models.carrier import (
    CarrierInteractionRequest,
    CarrierInteractionResponse,
    CarrierHistoryResponse,
)
from app.db.repositories.carrier_repo import (
    insert_interaction,
    get_interactions_by_mc,
)
from app.utils.fmcsa import ensure_mc_prefix


def log_interaction(
    req: CarrierInteractionRequest,
) -> CarrierInteractionResponse:
    record = insert_interaction(
        {
            "mc_number": ensure_mc_prefix(req.mc_number),
            "carrier_name": req.carrier_name,
            "call_id": req.call_id,
            "call_length_seconds": req.call_length_seconds,
            "outcome": req.outcome,
            "load_id": req.load_id,
            "notes": req.notes,
        }
    )
    return CarrierInteractionResponse(**record)


def get_carrier_history(mc_number: str) -> CarrierHistoryResponse:
    rows = get_interactions_by_mc(mc_number)
    interactions = [CarrierInteractionResponse(**r) for r in rows]
    return CarrierHistoryResponse(
        mc_number=mc_number,
        total_interactions=len(interactions),
        interactions=interactions,
    )
