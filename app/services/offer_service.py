from app.models.offer import OfferCreateRequest, OfferResponse
from app.db.repositories.load_repo import get_load_by_id
from app.db.repositories.offer_repo import insert_offer


def create_offer(
    req: OfferCreateRequest,
    rate_floor_percent: float,
    rate_ceiling_percent: float,
) -> tuple[OfferResponse, None] | tuple[None, str]:
    load = get_load_by_id(req.load_id)
    if not load:
        return None, f"Load {req.load_id} not found"

    floor = round(load["loadboard_rate"] * rate_floor_percent, 2)
    ceiling = round(load["loadboard_rate"] * rate_ceiling_percent, 2)

    result = insert_offer(
        {
            "call_id": req.call_id,
            "load_id": req.load_id,
            "mc_number": req.mc_number,
            "offer_amount": req.offer_amount,
            "offer_type": req.offer_type.value,
            "round_number": req.round_number,
            "status": req.status.value,
            "notes": req.notes,
        }
    )

    return OfferResponse(
        offer_id=result["offer_id"],
        call_id=result.get("call_id"),
        load_id=result["load_id"],
        mc_number=result["mc_number"],
        offer_amount=result["offer_amount"],
        offer_type=req.offer_type,
        round_number=result["round_number"],
        status=req.status,
        notes=result.get("notes", ""),
        created_at=result["created_at"],
        rate_floor=floor,
        rate_ceiling=ceiling,
    ), None
