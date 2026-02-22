from app.db.connection import get_db


def get_all_loads() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM loads WHERE status='available'"
        ).fetchall()
        return [dict(r) for r in rows]


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
