import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.db.city_data import CITY_COORDS, get_coords
from app.db.connection import get_db

LOADS_JSON_PATH = (
    Path(__file__).resolve().parent.parent.parent / "data" / "loads.json"
)


def _normalize_equipment(raw: str) -> str:
    s = (raw or "").lower().replace(" ", "_").replace("-", "_")
    return s if s else "dry_van"


def _get_coords(location: str) -> tuple[float, float]:
    """Look up city coordinates from the authoritative dataset."""
    return get_coords(location.strip())


def seed_cities() -> None:
    """Upsert all known cities into the `cities` table with region metadata."""
    with get_db() as conn:
        conn.executemany(
            """INSERT INTO cities (name, state, region, lat, lng)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   state=excluded.state,
                   region=excluded.region,
                   lat=excluded.lat,
                   lng=excluded.lng""",
            [
                (
                    name,
                    city_data["state"],
                    city_data["region"],
                    city_data["lat"],
                    city_data["lng"],
                )
                for name, city_data in CITY_COORDS.items()
            ],
        )


def _make_seed_loads() -> list[dict]:
    min_pickup = datetime.now(timezone.utc) + timedelta(hours=12)
    with open(LOADS_JSON_PATH, encoding="utf-8") as f:
        raw_loads = json.load(f)

    loads: list[dict] = []
    for r in raw_loads:
        pickup = datetime.fromisoformat(
            r["pickup_datetime"].replace("Z", "+00:00")
        )
        delivery = datetime.fromisoformat(
            r["delivery_datetime"].replace("Z", "+00:00")
        )
        delta = delivery - pickup
        if pickup < min_pickup:
            pickup = min_pickup
            delivery = pickup + delta
        origin_lat, origin_lng = _get_coords(r["origin"])
        dest_lat, dest_lng = _get_coords(r["destination"])
        loads.append(
            {
                "load_id": r["load_id"],
                "origin": r["origin"],
                "origin_lat": origin_lat,
                "origin_lng": origin_lng,
                "destination": r["destination"],
                "dest_lat": dest_lat,
                "dest_lng": dest_lng,
                "pickup_datetime": pickup.isoformat(),
                "delivery_datetime": delivery.isoformat(),
                "equipment_type": _normalize_equipment(
                    r.get("equipment_type", "")
                ),
                "loadboard_rate": float(r.get("loadboard_rate", 0)),
                "notes": r.get("notes", ""),
                "weight": int(r.get("weight", 0)),
                "commodity_type": r.get("commodity_type", ""),
                "num_of_pieces": int(r.get("num_of_pieces", 0)),
                "miles": int(r.get("miles", 0)),
                "dimensions": r.get("dimensions", ""),
            }
        )
    return loads


_DEFAULT_NEGOTIATION_SETTINGS = {
    "target_margin": 0.15,
    "min_margin": 0.05,
    "max_bump_above_loadboard": 0.03,
    "max_negotiation_rounds": 3,
    "max_offers_per_call": 3,
    "auto_transfer_threshold": 500,
    "deadhead_warning_miles": 150,
    "floor_rate_protection": 1,       # bool stored as 0/1
    "sentiment_escalation": 1,
    "prioritize_perishables": 1,
}

_DEFAULT_TEXT_SETTINGS = {
    "agent_greeting": "Thanks for calling, this is your AI carrier sales agent. How can I help you today?",
    "agent_tone": "professional",
}


def seed_negotiation_settings() -> None:
    """Insert default negotiation settings if not already present."""
    with get_db() as conn:
        for key, value in _DEFAULT_NEGOTIATION_SETTINGS.items():
            conn.execute(
                """INSERT INTO negotiation_settings (key, value)
                   VALUES (?, ?)
                   ON CONFLICT(key) DO NOTHING""",
                (key, value),
            )
        for key, text_value in _DEFAULT_TEXT_SETTINGS.items():
            conn.execute(
                """INSERT INTO negotiation_settings (key, text_value)
                   VALUES (?, ?)
                   ON CONFLICT(key) DO NOTHING""",
                (key, text_value),
            )


def seed_loads() -> None:
    """Insert seed loads if table is empty, and reset booking state on every startup."""
    with get_db() as conn:
        conn.execute(
            "UPDATE loads SET status='available', booked_at=NULL "
            "WHERE status='booked'"
        )
        conn.execute("DELETE FROM booked_loads")

        if conn.execute("SELECT COUNT(*) FROM loads").fetchone()[0] > 0:
            return
        for load in _make_seed_loads():
            conn.execute(
                """INSERT INTO loads
                   (load_id, origin, origin_lat, origin_lng, destination,
                    dest_lat, dest_lng, pickup_datetime, delivery_datetime,
                    equipment_type, loadboard_rate, notes, weight,
                    commodity_type, num_of_pieces, miles, dimensions)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    load["load_id"],
                    load["origin"],
                    load["origin_lat"],
                    load["origin_lng"],
                    load["destination"],
                    load["dest_lat"],
                    load["dest_lng"],
                    load["pickup_datetime"],
                    load["delivery_datetime"],
                    load["equipment_type"],
                    load["loadboard_rate"],
                    load["notes"],
                    load["weight"],
                    load["commodity_type"],
                    load["num_of_pieces"],
                    load["miles"],
                    load["dimensions"],
                ),
            )
