import uuid
from datetime import datetime

from app.db.connection import get_db


def insert_offer(offer: dict) -> dict:
    offer["offer_id"] = f"OFF-{uuid.uuid4().hex[:8]}"
    offer["created_at"] = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO offers
               (offer_id, call_id, load_id, mc_number,
                offer_amount, offer_type, round_number,
                status, notes, created_at,
                original_rate, rate_difference,
                rate_difference_pct,
                original_pickup_datetime,
                agreed_pickup_datetime, pickup_changed)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                offer["offer_id"],
                offer.get("call_id"),
                offer["load_id"],
                offer["mc_number"],
                offer["offer_amount"],
                offer["offer_type"],
                offer.get("round_number", 1),
                offer.get("status", "pending"),
                offer.get("notes", ""),
                offer["created_at"],
                offer.get("original_rate"),
                offer.get("rate_difference"),
                offer.get("rate_difference_pct"),
                offer.get("original_pickup_datetime"),
                offer.get("agreed_pickup_datetime"),
                offer.get("pickup_changed", False),
            ),
        )
    return offer
