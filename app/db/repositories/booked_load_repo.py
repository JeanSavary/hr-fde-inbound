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
            """SELECT bl.*,
                      l.origin        AS lane_origin,
                      l.destination   AS lane_destination,
                      l.equipment_type,
                      l.loadboard_rate,
                      c.negotiation_rounds,
                      c.sentiment
               FROM booked_loads bl
               LEFT JOIN loads l ON bl.load_id = l.load_id
               LEFT JOIN calls c ON bl.call_id = c.call_id
               WHERE bl.load_id = ?""",
            (load_id,),
        ).fetchone()
    return dict(row) if row else None


def get_all_booked_loads(
    offset: int = 0, limit: int = 20, since: str | None = None
) -> tuple[list[dict], int]:
    clauses: list[str] = []
    params: list = []
    if since:
        clauses.append("bl.created_at >= ?")
        params.append(since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM booked_loads bl {where}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"""SELECT bl.*,
                      l.origin        AS lane_origin,
                      l.destination   AS lane_destination,
                      l.equipment_type,
                      l.loadboard_rate,
                      c.negotiation_rounds,
                      c.sentiment
               FROM booked_loads bl
               LEFT JOIN loads l ON bl.load_id = l.load_id
               LEFT JOIN calls c ON bl.call_id = c.call_id
               {where}
               ORDER BY bl.created_at DESC
               LIMIT ? OFFSET ?""",
            params + [limit, offset],
        ).fetchall()
    return [dict(r) for r in rows], total


def get_booked_loads_kpis(since: str | None = None) -> dict:
    """Aggregate KPIs across all bookings in the period."""
    clauses: list[str] = []
    params: list = []
    if since:
        clauses.append("bl.created_at >= ?")
        params.append(since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_db() as conn:
        row = conn.execute(
            f"""SELECT
                    COUNT(*) AS total_bookings,
                    COALESCE(SUM(bl.agreed_rate), 0) AS total_revenue,
                    AVG(CASE WHEN l.loadboard_rate > 0 AND bl.agreed_rate IS NOT NULL
                        THEN ((l.loadboard_rate - bl.agreed_rate) / l.loadboard_rate) * 100
                        ELSE NULL END) AS avg_margin,
                    AVG(c.negotiation_rounds) AS avg_rounds
                FROM booked_loads bl
                LEFT JOIN loads l ON bl.load_id = l.load_id
                LEFT JOIN calls c ON bl.call_id = c.call_id
                {where}""",
            params,
        ).fetchone()

    return {
        "kpi_total_bookings": row[0] or 0,
        "kpi_total_revenue": round(row[1], 2) if row[1] else 0,
        "kpi_avg_margin": round(row[2], 1) if row[2] is not None else None,
        "kpi_avg_rounds": round(row[3], 1) if row[3] is not None else None,
    }
