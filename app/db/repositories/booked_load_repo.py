import uuid
from datetime import datetime

from app.db.connection import get_db


def insert_booked_load(booking: dict) -> dict:
    booking["id"] = f"BK-{uuid.uuid4().hex[:8]}"
    booking["created_at"] = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO booked_loads
               (id, load_id, mc_number, carrier_name,
                agreed_rate, agreed_pickup_datetime,
                offer_id, call_id, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                booking["id"],
                booking["load_id"],
                booking["mc_number"],
                booking.get("carrier_name"),
                booking["agreed_rate"],
                booking.get("agreed_pickup_datetime"),
                booking.get("offer_id"),
                booking.get("call_id"),
                booking["created_at"],
            ),
        )
        conn.execute(
            """UPDATE loads SET status='booked', booked_at=?
               WHERE load_id=?""",
            (booking["created_at"], booking["load_id"]),
        )
    return booking


def get_booked_load(load_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM booked_loads WHERE load_id=?",
            (load_id,),
        ).fetchone()
    return dict(row) if row else None


def get_all_booked_loads() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM booked_loads ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]
