from typing import Optional

from app.db.connection import get_db


def get_all_loads() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM loads WHERE status='available'"
        ).fetchall()
        return [dict(r) for r in rows]


_ALLOWED_SORT_FIELDS = {
    "pickup_datetime",
    "loadboard_rate",
    "miles",
    "created_at",
    "weight",
}
_ALLOWED_ORDER = {"asc", "desc"}


def _build_order_clause(sort_by: str, sort_order: str) -> str:
    """Build a multi-column ORDER BY clause from comma-separated sort fields."""
    fields = [s.strip() for s in sort_by.split(",") if s.strip()]
    orders = [s.strip() for s in sort_order.split(",") if s.strip()]
    # Pad orders to match fields length
    while len(orders) < len(fields):
        orders.append("asc")

    parts: list[str] = []
    for field, ord_ in zip(fields, orders):
        if field in _ALLOWED_SORT_FIELDS:
            safe_ord = ord_.upper() if ord_.lower() in _ALLOWED_ORDER else "ASC"
            parts.append(f"loads.{field} {safe_ord}")

    return f"ORDER BY {', '.join(parts)}" if parts else "ORDER BY loads.pickup_datetime ASC"


def get_loads_paginated(
    status: str | None = None,
    equipment_type: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    since: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort_by: str = "pickup_datetime",
    sort_order: str = "asc",
    skip_pagination: bool = False,
) -> tuple[list[dict], int]:
    clauses: list[str] = []
    params: list = []

    if since:
        clauses.append("loads.created_at >= ?")
        params.append(since)
    if status:
        clauses.append("loads.status = ?")
        params.append(status)
    if equipment_type:
        clauses.append("loads.equipment_type = ?")
        params.append(equipment_type)
    if origin:
        clauses.append("loads.origin LIKE ?")
        params.append(f"%{origin}%")
    if destination:
        clauses.append("loads.destination LIKE ?")
        params.append(f"%{destination}%")

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    order_clause = _build_order_clause(sort_by, sort_order)

    select_expr = (
        f"SELECT loads.*, "
        f"(SELECT COUNT(*) FROM offers WHERE offers.load_id = loads.load_id) AS pitch_count, "
        f"(SELECT COUNT(*) FROM calls WHERE calls.load_id = loads.load_id "
        f"AND calls.outcome = 'carrier_thinking') AS active_thinking_calls "
        f"FROM loads {where} {order_clause}"
    )

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM loads {where}", params
        ).fetchone()[0]

        if skip_pagination:
            rows = conn.execute(select_expr, params).fetchall()
        else:
            rows = conn.execute(
                f"{select_expr} LIMIT ? OFFSET ?",
                params + [page_size, (page - 1) * page_size],
            ).fetchall()

    return [dict(r) for r in rows], total


def get_load_by_id(load_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM loads WHERE load_id=?", (load_id,)
        ).fetchone()
        return dict(row) if row else None


def mark_load_booked(load_id: str, booked_at: str) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE loads SET status='booked', booked_at=? WHERE load_id=?",
            (booked_at, load_id),
        )


def get_loads_kpis(
    since: str | None = None,
    status: str | None = None,
    target_margin: float = 0.15,
) -> dict:
    """Aggregate KPIs and urgency data across all loads in the period."""
    clauses: list[str] = []
    params: list = []
    if since:
        clauses.append("loads.created_at >= ?")
        params.append(since)
    if status:
        clauses.append("loads.status = ?")
        params.append(status)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    floor_factor = 1 - target_margin

    with get_db() as conn:
        row = conn.execute(
            f"SELECT "
            f"  COUNT(*) AS total_loads, "
            f"  AVG(CASE WHEN loads.miles > 0 "
            f"      THEN loads.loadboard_rate * ? / loads.miles "
            f"      ELSE NULL END) AS avg_rpm "
            f"FROM loads {where}",
            [floor_factor] + params,
        ).fetchone()

        urgency_rows = conn.execute(
            f"SELECT loads.commodity_type, loads.notes, loads.created_at, "
            f"  (SELECT COUNT(*) FROM offers WHERE offers.load_id = loads.load_id) AS pitch_count "
            f"FROM loads {where}",
            params,
        ).fetchall()

    return {
        "total_loads": row[0] or 0,
        "avg_rate_per_mile": round(row[1], 2) if row[1] is not None else None,
        "urgency_data": [dict(r) for r in urgency_rows],
    }
