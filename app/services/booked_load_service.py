import uuid

from app.models.offer import (
    BookedLoadRequest,
    BookedLoadResponse,
    PaginatedBookedLoads,
)
from app.db.repositories.load_repo import get_load_by_id
from app.db.repositories.booked_load_repo import (
    insert_booked_load,
    get_booked_load,
    get_all_booked_loads,
    get_booked_loads_kpis,
)
from app.db.repositories.negotiation_settings_repo import get_all_settings
from app.utils.period import period_since


def _enrich_booking(record: dict) -> BookedLoadResponse:
    """Add computed margin and booked_at to a booking record."""
    margin = None
    loadboard_rate = record.get("loadboard_rate")
    agreed_rate = record.get("agreed_rate")
    if loadboard_rate and agreed_rate and loadboard_rate > 0:
        margin = round(
            ((loadboard_rate - agreed_rate) / loadboard_rate) * 100, 1
        )
    record["margin"] = margin
    record["booked_at"] = record.get("created_at")
    return BookedLoadResponse(**record)


def book_load(
    req: BookedLoadRequest,
) -> tuple[BookedLoadResponse, None] | tuple[None, str]:
    load = get_load_by_id(req.load_id)
    if not load:
        return None, f"Load {req.load_id} not found"
    if load.get("status") == "booked":
        return None, f"Load {req.load_id} is already booked"

    ns = get_all_settings()
    target_margin = ns.get("target_margin", 0.15)
    floor_rate = round(load["loadboard_rate"] * (1 - target_margin), 2)
    agreed_rate = (
        req.agreed_rate
        if req.agreed_rate is not None
        else floor_rate
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
    return _enrich_booking(record) if record else None


def list_bookings(
    offset: int = 0,
    limit: int = 20,
    page: int = 1,
    page_size: int = 20,
    period: str = "last_month",
) -> PaginatedBookedLoads:
    since = period_since(period)
    rows, total = get_all_booked_loads(offset=offset, limit=limit, since=since)
    kpis = get_booked_loads_kpis(since)
    return PaginatedBookedLoads(
        items=[_enrich_booking(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        **kpis,
    )
