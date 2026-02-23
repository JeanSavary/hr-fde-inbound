from typing import Optional

from app.db.connection import get_db


def get_all_loads() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM loads WHERE status='available'"
        ).fetchall()
        return [dict(r) for r in rows]


_ALLOWED_SORT_FIELDS = {"pickup_datetime", "loadboard_rate", "miles", "created_at", "weight"}
_ALLOWED_ORDER = {"asc", "desc"}


def get_loads_paginated(
    status: str | None = None,
    equipment_type: str | None = None,
    origin: str | None = None,
    destination: str | None = None,
    page: int = 1,
    page_size: int = 50,
    sort: str = "pickup_datetime",
    order: str = "asc",
) -> tuple[list[dict], int]:
    clauses: list[str] = []
    params: list = []

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

    # Validate sort/order against whitelist to prevent SQL injection
    if sort not in _ALLOWED_SORT_FIELDS:
        sort = "pickup_datetime"
    if order.lower() not in _ALLOWED_ORDER:
        order = "asc"

    order_clause = f"ORDER BY loads.{sort} {order.upper()}"

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM loads {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT loads.*, "
            f"(SELECT COUNT(*) FROM offers WHERE offers.load_id = loads.load_id) AS pitch_count "
            f"FROM loads {where} "
            f"{order_clause} LIMIT ? OFFSET ?",
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
