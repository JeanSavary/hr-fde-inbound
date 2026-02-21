import uuid
from datetime import datetime

from app.db.connection import get_db


def insert_call(call: dict) -> dict:
    call["id"] = f"CALL-{uuid.uuid4().hex[:8]}"
    call["created_at"] = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO calls
               (id, call_id, mc_number, carrier_name, lane_origin,
                lane_destination, equipment_type, load_id, initial_rate,
                final_rate, negotiation_rounds, carrier_phone,
                special_requests, outcome, sentiment, duration_seconds,
                transcript, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                call["id"],
                call["call_id"],
                call.get("mc_number"),
                call.get("carrier_name"),
                call.get("lane_origin"),
                call.get("lane_destination"),
                call.get("equipment_type"),
                call.get("load_id"),
                call.get("initial_rate"),
                call.get("final_rate"),
                call.get("negotiation_rounds", 0),
                call.get("carrier_phone"),
                call.get("special_requests"),
                call["outcome"],
                call["sentiment"],
                call.get("duration_seconds"),
                call.get("transcript"),
                call["created_at"],
            ),
        )
    return call
