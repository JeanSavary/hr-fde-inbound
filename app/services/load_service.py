from datetime import datetime, timedelta, timezone

from app.db.repositories.load_repo import get_all_loads, get_load_by_id
from app.models.load import (
    AlternativeLoad,
    Load,
    LoadSearchResponse,
    SearchResultLoad,
)
from app.db.city_data import get_location_meta
from app.utils.geo import haversine_miles, resolve_location

# How far beyond the requested radius we still surface alternatives
_ALT_RADIUS_MULTIPLIER = 3
_ALT_MAX_ORIGIN_MILES = 250  # hard cap so we don't surface coast-to-coast
_ALT_MAX_DEST_MILES = 300
_ALT_MAX_RESULTS = 10


def _parse_pickup(dt_str: str) -> datetime:
    pickup = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if pickup.tzinfo is None:
        pickup = pickup.replace(tzinfo=timezone.utc)
    return pickup


def _normalize_equipment(raw: str) -> str:
    return raw.lower().strip().replace(" ", "_").replace("-", "_")


def _equipment_label(eq: str) -> str:
    return eq.replace("_", " ").title()


def _origin_ok(
    load: dict, o_type: str, o_val: object, radius_miles: int
) -> tuple[bool, float]:
    """
    Return (origin_ok, o_dist). o_dist is used for deadhead and alternatives.
    """
    load_meta = get_location_meta(load["origin"])
    if o_type == "city":
        name, o_lat, o_lng = o_val
        o_dist = haversine_miles(
            o_lat, o_lng, load["origin_lat"], load["origin_lng"]
        )
        return (o_dist <= radius_miles, o_dist)
    if o_type == "state":
        return (
            bool(load_meta and load_meta[0] == o_val),
            0.0 if not load_meta else 0.0,
        )
    if o_type == "region":
        return (
            bool(load_meta and load_meta[1] == o_val),
            0.0 if not load_meta else 0.0,
        )
    return (False, 0.0)


def _dest_ok(
    load: dict, d_type: str | None, d_val: object | None, radius_miles: int
) -> tuple[bool, float | None]:
    """Return (dest_ok, d_dist). d_dist is used for deadend."""
    if d_type is None or d_val is None:
        return (True, None)
    load_meta = get_location_meta(load["destination"])
    if d_type == "city":
        name, d_lat, d_lng = d_val
        d_dist = haversine_miles(
            d_lat, d_lng, load["dest_lat"], load["dest_lng"]
        )
        return (d_dist <= radius_miles, d_dist)
    if d_type == "state":
        return (
            bool(load_meta and load_meta[0] == d_val),
            0.0 if load_meta else None,
        )
    if d_type == "region":
        return (
            bool(load_meta and load_meta[1] == d_val),
            0.0 if load_meta else None,
        )
    return (False, None)


def _alt_origin_ok(
    load: dict, o_type: str, o_val: object, alt_cap: float
) -> bool:
    """Whether load qualifies for alternatives by origin."""
    if o_type == "city":
        name, o_lat, o_lng = o_val
        o_dist = haversine_miles(
            o_lat, o_lng, load["origin_lat"], load["origin_lng"]
        )
        return o_dist <= alt_cap
    load_meta = get_location_meta(load["origin"])
    if o_type == "state":
        return bool(load_meta and load_meta[0] == o_val)
    if o_type == "region":
        return bool(load_meta and load_meta[1] == o_val)
    return False


def _alt_dest_ok(
    load: dict, d_type: str | None, d_val: object | None, alt_cap: float
) -> bool:
    """Whether load qualifies for alternatives by destination."""
    if d_type is None or d_val is None:
        return True
    if d_type == "city":
        name, d_lat, d_lng = d_val
        d_dist = haversine_miles(
            d_lat, d_lng, load["dest_lat"], load["dest_lng"]
        )
        return d_dist <= alt_cap
    load_meta = get_location_meta(load["destination"])
    if d_type == "state":
        return bool(load_meta and load_meta[0] == d_val)
    if d_type == "region":
        return bool(load_meta and load_meta[1] == d_val)
    return False


def _resolved_label(typ: str, val: object) -> str:
    """Human-readable label for origin_resolved / destination_resolved."""
    if typ == "city":
        return val[0]
    return str(val)


async def search_loads(
    origin: str,
    equipment_type: str,
    destination: str | None = None,
    pickup_date: str | None = None,
    radius_miles: int = 75,
    pickup_window_hours: int | None = None,
    max_distance_miles: int | None = None,
) -> LoadSearchResponse:
    o_type, o_val = await resolve_location(origin)
    d_type, d_val = None, None
    if destination:
        d_type, d_val = await resolve_location(destination)

    equip = _normalize_equipment(equipment_type)

    now = datetime.now(timezone.utc)
    window_end = (
        now + timedelta(hours=pickup_window_hours)
        if pickup_window_hours
        else None
    )

    alt_origin_cap = min(
        radius_miles * _ALT_RADIUS_MULTIPLIER, _ALT_MAX_ORIGIN_MILES
    )
    alt_dest_cap = min(
        radius_miles * _ALT_RADIUS_MULTIPLIER, _ALT_MAX_DEST_MILES
    )

    matched_ids: set[str] = set()
    matches: list[SearchResultLoad] = []
    alternatives: list[AlternativeLoad] = []

    for load in get_all_loads():
        origin_ok, o_dist = _origin_ok(load, o_type, o_val, radius_miles)
        dest_ok, d_dist = _dest_ok(load, d_type, d_val, radius_miles)

        # ── Strict pass ──────────────────────────────────────────────
        equip_ok = load["equipment_type"] == equip
        max_dist_ok = (
            max_distance_miles is None or load["miles"] <= max_distance_miles
        )
        date_ok = not pickup_date or (
            load["pickup_datetime"][:10] == pickup_date[:10]
        )
        window_ok = True
        if window_end is not None:
            pickup_dt = _parse_pickup(load["pickup_datetime"])
            window_ok = now <= pickup_dt <= window_end

        if (
            equip_ok
            and origin_ok
            and dest_ok
            and max_dist_ok
            and date_ok
            and window_ok
        ):
            matched_ids.add(load["load_id"])
            miles = load["miles"] or 1
            matches.append(
                SearchResultLoad(
                    **load,
                    rate_per_mile=round(load["loadboard_rate"] / miles, 2),
                    deadhead_miles=round(o_dist, 1),
                    deadend_miles=round(d_dist, 1)
                    if d_dist is not None
                    else 0.0,
                )
            )
            continue

        # ── Alternatives pass — only when strict matches are scarce ─
        if not _alt_origin_ok(load, o_type, o_val, alt_origin_cap):
            continue
        if not _alt_dest_ok(load, d_type, d_val, alt_dest_cap):
            continue

        diffs: list[str] = []
        o_label = _resolved_label(o_type, o_val)
        d_label = _resolved_label(d_type, d_val) if d_val else ""

        if not equip_ok:
            diffs.append(
                f"Equipment is {_equipment_label(load['equipment_type'])}"
                f", not {_equipment_label(equip)}"
            )
        if not origin_ok:
            if o_type == "city":
                diffs.append(
                    f"Pickup is in {load['origin']} —"
                    f" {round(o_dist)} mi from {o_label}"
                    f" ({round(o_dist - radius_miles)} mi outside your"
                    f" {radius_miles}-mile radius)"
                )
            else:
                diffs.append(
                    f"Pickup is in {load['origin']} (not in {o_label})"
                )
        if not dest_ok and d_val is not None:
            if d_type == "city":
                diffs.append(
                    f"Delivers to {load['destination']} —"
                    f" {round(d_dist)} mi from {d_label}"
                    f" ({round(d_dist - radius_miles)} mi outside your"
                    f" {radius_miles}-mile radius)"
                )
            else:
                diffs.append(
                    f"Delivers to {load['destination']} (not in {d_label})"
                )
        if not max_dist_ok:
            diffs.append(
                f"Haul distance is {load['miles']} mi"
                f" (exceeds your {max_distance_miles}-mile max)"
            )
        if not date_ok:
            diffs.append(
                f"Pickup date is {load['pickup_datetime'][:10]}"
                f", not {pickup_date}"
            )
        if not window_ok:
            pickup_dt = _parse_pickup(load["pickup_datetime"])
            diffs.append(
                f"Pickup is at {pickup_dt.strftime('%Y-%m-%d %H:%M UTC')}"
                f", outside your {pickup_window_hours}-hour window"
            )

        if not diffs:
            continue

        miles = load["miles"] or 1
        alternatives.append(
            AlternativeLoad(
                **load,
                rate_per_mile=round(load["loadboard_rate"] / miles, 2),
                deadhead_miles=round(o_dist, 1),
                deadend_miles=round(d_dist, 1) if d_dist is not None else 0.0,
                differences=diffs,
            )
        )

    matches.sort(key=lambda m: m.loadboard_rate, reverse=True)

    # Alternatives are only surfaced when strict matches are scarce,
    # and the combined total must never exceed 5.
    _EXACT_THRESHOLD = 3
    _TOTAL_CAP = 5

    if len(matches) >= _EXACT_THRESHOLD:
        alternatives = []
    else:
        slots = _TOTAL_CAP - len(matches)
        alternatives.sort(
            key=lambda a: (len(a.differences), -a.loadboard_rate)
        )
        alternatives = alternatives[:slots]

    return LoadSearchResponse(
        loads=matches,
        alternative_loads=alternatives,
        origin_resolved=_resolved_label(o_type, o_val),
        destination_resolved=_resolved_label(d_type, d_val) if d_val else None,
        radius_miles=radius_miles,
        total_found=len(matches),
        total_alternatives=len(alternatives),
    )


def get_load(load_id: str) -> Load | None:
    load = get_load_by_id(load_id)
    return Load(**load) if load else None
