import json
import uuid
from datetime import datetime
from typing import Optional

from app.db.connection import get_db


def insert_call(call: dict) -> dict:
    call["id"] = f"CALL-{uuid.uuid4().hex[:8]}"
    call["created_at"] = datetime.utcnow().isoformat()

    key_points_json = None
    if call.get("key_points"):
        key_points_json = json.dumps(call["key_points"])

    with get_db() as conn:
        conn.execute(
            """INSERT INTO calls
               (id, call_id, mc_number, carrier_name, lane_origin,
                lane_destination, equipment_type, load_id,
                initial_rate, final_rate, negotiation_rounds,
                carrier_phone, special_requests, outcome,
                sentiment, duration_seconds, transcript,
                summary, key_points, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
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
                call.get("summary"),
                key_points_json,
                call["created_at"],
            ),
        )
    return call


def _row_to_dict(row) -> dict:
    d = dict(row)
    if d.get("key_points"):
        try:
            d["key_points"] = json.loads(d["key_points"])
        except (json.JSONDecodeError, TypeError):
            d["key_points"] = None
    return d


def get_call_by_call_id(call_id: str) -> Optional[dict]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM calls WHERE call_id = ?", (call_id,)
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def get_all_calls(
    outcome: Optional[str] = None,
    sentiment: Optional[str] = None,
    mc_number: Optional[str] = None,
    since: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[dict], int]:
    clauses: list[str] = []
    params: list = []

    if since:
        clauses.append("created_at >= ?")
        params.append(since)
    if outcome:
        clauses.append("outcome = ?")
        params.append(outcome)
    if sentiment:
        clauses.append("sentiment = ?")
        params.append(sentiment)
    if mc_number:
        clauses.append("mc_number = ?")
        params.append(mc_number)

    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM calls {where}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"SELECT * FROM calls {where} "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [page_size, (page - 1) * page_size],
        ).fetchall()

    return [_row_to_dict(r) for r in rows], total


def get_calls_kpis(since: Optional[str] = None) -> dict:
    """Aggregate KPIs across all calls in the period."""
    clauses: list[str] = []
    params: list = []
    if since:
        clauses.append("created_at >= ?")
        params.append(since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        row = conn.execute(
            f"SELECT "
            f"  COUNT(*) AS total, "
            f"  SUM(CASE WHEN outcome='booked' THEN 1 ELSE 0 END) AS booked, "
            f"  COALESCE(SUM(duration_seconds), 0) AS total_duration "
            f"FROM calls {where}",
            params,
        ).fetchone()

    total = row[0] or 0
    booked = row[1] or 0
    total_duration = row[2] or 0

    return {
        "kpi_total_calls": total,
        "kpi_booking_rate": round((booked / total) * 100, 1) if total > 0 else 0,
        "kpi_avg_duration": round(total_duration / total) if total > 0 else 0,
        "kpi_total_duration": total_duration,
    }
