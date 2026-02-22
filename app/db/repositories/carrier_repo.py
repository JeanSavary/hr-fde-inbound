import uuid
from datetime import datetime

from app.db.connection import get_db


def insert_interaction(interaction: dict) -> dict:
    interaction["id"] = f"CI-{uuid.uuid4().hex[:8]}"
    interaction["created_at"] = datetime.utcnow().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO carrier_interactions
               (id, mc_number, carrier_name, call_id,
                call_length_seconds, outcome, load_id,
                notes, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                interaction["id"],
                interaction["mc_number"],
                interaction.get("carrier_name"),
                interaction.get("call_id"),
                interaction.get("call_length_seconds"),
                interaction.get("outcome"),
                interaction.get("load_id"),
                interaction.get("notes", ""),
                interaction["created_at"],
            ),
        )
    return interaction


def get_interactions_by_mc(mc_number: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM carrier_interactions
               WHERE mc_number=? ORDER BY created_at DESC""",
            (mc_number,),
        ).fetchall()
    return [dict(r) for r in rows]
