from app.db.connection import get_db


def get_calls_by_date(date_str: str) -> list[dict]:
    """Get all calls where created_at starts with date_str (YYYY-MM-DD)."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM calls WHERE created_at LIKE ?",
            (f"{date_str}%",),
        ).fetchall()
    return [dict(r) for r in rows]


def get_bookings_with_loads_by_date(date_str: str) -> list[dict]:
    """Get bookings for a date, joined with loads for rate data."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT bl.*, l.loadboard_rate
            FROM booked_loads bl
            LEFT JOIN loads l ON bl.load_id = l.load_id
            WHERE bl.created_at LIKE ?
        """, (f"{date_str}%",)).fetchall()
    return [dict(r) for r in rows]


def get_all_bookings_with_loads() -> list[dict]:
    """Get all bookings joined with loads for rate data."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT bl.*, l.loadboard_rate
            FROM booked_loads bl
            LEFT JOIN loads l ON bl.load_id = l.load_id
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


def get_dashboard_data() -> dict:
    with get_db() as conn:
        calls = [
            dict(r) for r in conn.execute("SELECT * FROM calls").fetchall()
        ]
        offers = [
            dict(r) for r in conn.execute("SELECT * FROM offers").fetchall()
        ]

    total = len(calls)
    if total == 0:
        return {
            "total_calls": 0,
            "avg_duration_seconds": None,
            "calls_by_outcome": {},
            "sentiment_distribution": {},
            "booking_rate_percent": 0.0,
            "avg_negotiation_rounds": None,
            "avg_rate_differential_percent": None,
            "total_revenue": 0.0,
            "unique_carriers": 0,
            "top_lanes": [],
            "equipment_demand": {},
            "recent_calls": [],
            "recent_offers": [],
        }

    outcomes: dict[str, int] = {}
    sentiments: dict[str, int] = {}
    for c in calls:
        outcomes[c["outcome"]] = outcomes.get(c["outcome"], 0) + 1
        sentiments[c["sentiment"]] = sentiments.get(c["sentiment"], 0) + 1

    durations = [c["duration_seconds"] for c in calls if c["duration_seconds"]]
    avg_dur = sum(durations) / len(durations) if durations else None

    booked_calls = [c for c in calls if c["outcome"] == "booked"]
    booked = len(booked_calls)
    booking_rate = (booked / total * 100) if total else 0.0

    rounds = [
        c["negotiation_rounds"]
        for c in booked_calls
        if c["negotiation_rounds"]
    ]
    avg_rounds = sum(rounds) / len(rounds) if rounds else None

    diffs = []
    for c in booked_calls:
        if c["initial_rate"] and c["final_rate"] and c["initial_rate"] > 0:
            diffs.append(
                ((c["final_rate"] - c["initial_rate"]) / c["initial_rate"])
                * 100
            )
    avg_diff = sum(diffs) / len(diffs) if diffs else None

    total_rev = (
        sum(c["final_rate"] for c in booked_calls if c["final_rate"]) or 0.0
    )

    lanes: dict[str, int] = {}
    equip: dict[str, int] = {}
    for c in calls:
        if c["lane_origin"] and c["lane_destination"]:
            lane = f"{c['lane_origin']} → {c['lane_destination']}"
            lanes[lane] = lanes.get(lane, 0) + 1
        if c["equipment_type"]:
            equip[c["equipment_type"]] = equip.get(c["equipment_type"], 0) + 1

    top_lanes = sorted(
        [{"lane": k, "count": v} for k, v in lanes.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:10]

    return {
        "total_calls": total,
        "avg_duration_seconds": avg_dur,
        "calls_by_outcome": outcomes,
        "sentiment_distribution": sentiments,
        "booking_rate_percent": round(booking_rate, 1),
        "avg_negotiation_rounds": round(avg_rounds, 1) if avg_rounds else None,
        "avg_rate_differential_percent": round(avg_diff, 1)
        if avg_diff
        else None,
        "total_revenue": round(total_rev, 2),
        "unique_carriers": len(
            set(c["mc_number"] for c in calls if c["mc_number"])
        ),
        "top_lanes": top_lanes,
        "equipment_demand": equip,
        "recent_calls": calls[-10:][::-1],
        "recent_offers": offers[-10:][::-1],
    }
