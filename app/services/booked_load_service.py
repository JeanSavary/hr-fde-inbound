import uuid

from app.models.offer import BookedLoadRequest, BookedLoadResponse
from app.db.repositories.load_repo import get_load_by_id
from app.db.repositories.booked_load_repo import (
    insert_booked_load,
    get_booked_load,
    get_all_booked_loads,
)


def book_load(
    req: BookedLoadRequest,
) -> tuple[BookedLoadResponse, None] | tuple[None, str]:
    load = get_load_by_id(req.load_id)
    if not load:
        return None, f"Load {req.load_id} not found"
    if load.get("status") == "booked":
        return None, f"Load {req.load_id} is already booked"

    agreed_rate = (
        req.agreed_rate
        if req.agreed_rate is not None
        else load["loadboard_rate"]
    )
    agreed_pickup_datetime = (
        req.agreed_pickup_datetime
        if req.agreed_pickup_datetime is not None
        else load["pickup_datetime"]
    )

    record = insert_booked_load(
        {
            "load_id": req.load_id,
            "mc_number": req.mc_number,
            "carrier_name": req.carrier_name,
            "agreed_rate": agreed_rate,
            "agreed_pickup_datetime": agreed_pickup_datetime,
            "offer_id": f"OF-{uuid.uuid4().hex[:8]}",
            "call_id": req.call_id,
        }
    )
    return BookedLoadResponse(**record), None


def get_booking(
    load_id: str,
) -> BookedLoadResponse | None:
    record = get_booked_load(load_id)
    return BookedLoadResponse(**record) if record else None


def list_bookings() -> list[BookedLoadResponse]:
    return [BookedLoadResponse(**r) for r in get_all_booked_loads()]
