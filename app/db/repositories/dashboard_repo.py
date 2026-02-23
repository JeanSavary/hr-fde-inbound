from app.db.connection import get_db


def get_calls_since(since: str | None = None) -> list[dict]:
    """Get all calls, optionally filtered by created_at >= since."""
    with get_db() as conn:
        if since:
            rows = conn.execute(
                "SELECT * FROM calls WHERE created_at >= ? ORDER BY created_at DESC",
                (since,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM calls ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


def get_bookings_with_loads_since(since: str | None = None) -> list[dict]:
    """Get bookings joined with loads, optionally filtered by date."""
    with get_db() as conn:
        if since:
            rows = conn.execute("""
                SELECT bl.*, l.loadboard_rate
                FROM booked_loads bl
                LEFT JOIN loads l ON bl.load_id = l.load_id
                WHERE bl.created_at >= ?
                ORDER BY bl.created_at DESC
            """, (since,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT bl.*, l.loadboard_rate
                FROM booked_loads bl
                LEFT JOIN loads l ON bl.load_id = l.load_id
                ORDER BY bl.created_at DESC
            """).fetchall()
    return [dict(r) for r in rows]


def get_offers_for_calls(call_ids: list[str]) -> list[dict]:
    """Get offers associated with a list of call_ids."""
    if not call_ids:
        return []
    placeholders = ",".join("?" for _ in call_ids)
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM offers WHERE call_id IN ({placeholders})",
            call_ids,
        ).fetchall()
    return [dict(r) for r in rows]
