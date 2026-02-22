from datetime import datetime, timedelta, timezone

from app.db.repositories.load_repo import get_all_loads, get_load_by_id
from app.db.repositories.negotiation_settings_repo import get_all_settings
from app.models.load import (
    AlternativeLoad,
    Load,
    LoadSearchResponse,
    PickupRescheduleRequest,
    PickupRescheduleResponse,
    SearchResultLoad,
)
from app.models.location import ResolvedLocation
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
    load: dict, loc: ResolvedLocation, radius_miles: int
) -> tuple[bool, float]:
    """
    Return (origin_ok, o_dist). o_dist is deadhead miles.
    """
    if loc.is_city:
        o_dist = haversine_miles(
            loc.lat,
            loc.lng,
            load["origin_lat"],
            load["origin_lng"],
        )
        return (o_dist <= radius_miles, o_dist)
    load_meta = get_location_meta(load["origin"])
    if loc.is_state:
        return (bool(load_meta and load_meta[0] == loc.label), 0.0)
    if loc.is_region:
        return (bool(load_meta and load_meta[1] == loc.label), 0.0)
    return (False, 0.0)


def _dest_ok(
    load: dict,
    loc: ResolvedLocation | None,
    radius_miles: int,
) -> tuple[bool, float | None]:
    """Return (dest_ok, d_dist). d_dist is deadend miles."""
    if loc is None:
        return (True, None)
    if loc.is_city:
        d_dist = haversine_miles(
            loc.lat,
            loc.lng,
            load["dest_lat"],
            load["dest_lng"],
        )
        return (d_dist <= radius_miles, d_dist)
    load_meta = get_location_meta(load["destination"])
    if loc.is_state:
        return (
            bool(load_meta and load_meta[0] == loc.label),
            0.0 if load_meta else None,
        )
    if loc.is_region:
        return (
            bool(load_meta and load_meta[1] == loc.label),
            0.0 if load_meta else None,
        )
    return (False, None)


def _alt_origin_ok(load: dict, loc: ResolvedLocation, alt_cap: float) -> bool:
    """Whether load qualifies for alternatives by origin."""
    if loc.is_city:
        o_dist = haversine_miles(
            loc.lat,
            loc.lng,
            load["origin_lat"],
            load["origin_lng"],
        )
        return o_dist <= alt_cap
    load_meta = get_location_meta(load["origin"])
    if loc.is_state:
        return bool(load_meta and load_meta[0] == loc.label)
    if loc.is_region:
        return bool(load_meta and load_meta[1] == loc.label)
    return False


def _alt_dest_ok(
    load: dict,
    loc: ResolvedLocation | None,
    alt_cap: float,
) -> bool:
    """Whether load qualifies for alternatives by destination."""
    if loc is None:
        return True
    if loc.is_city:
        d_dist = haversine_miles(
            loc.lat,
            loc.lng,
            load["dest_lat"],
            load["dest_lng"],
        )
        return d_dist <= alt_cap
    load_meta = get_location_meta(load["destination"])
    if loc.is_state:
        return bool(load_meta and load_meta[0] == loc.label)
    if loc.is_region:
        return bool(load_meta and load_meta[1] == loc.label)
    return False


def _resolved_label(loc: ResolvedLocation) -> str:
    """Human-readable label for origin_resolved / destination_resolved."""
    return loc.label


async def search_loads(
    origin: str,
    equipment_type: str,
    destination: str | None = None,
    pickup_datetime: str | None = None,
    radius_miles: int = 75,
    pickup_window_hours: int | None = None,
    max_distance_miles: int | None = None,
    max_weight: int | None = None,
) -> LoadSearchResponse:
    o_loc = await resolve_location(origin)
    d_loc: ResolvedLocation | None = None
    if destination:
        d_loc = await resolve_location(destination)

    equip = _normalize_equipment(equipment_type)

    ns = get_all_settings()
    target_margin = ns.get("target_margin", 0.15)
    max_bump = ns.get("max_bump_above_loadboard", 0.03)

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
        origin_ok, o_dist = _origin_ok(load, o_loc, radius_miles)
        dest_ok, d_dist = _dest_ok(load, d_loc, radius_miles)

        equip_ok = load["equipment_type"] == equip
        max_dist_ok = (
            max_distance_miles is None
            or load["miles"] <= max_distance_miles
        )
        weight_ok = (
            max_weight is None
            or load["weight"] <= max_weight
        )
        date_ok = True
        if pickup_datetime:
            ask_dt = _parse_pickup(pickup_datetime)
            load_dt = _parse_pickup(load["pickup_datetime"])
            date_ok = load_dt.date() == ask_dt.date()
        window_ok = True
        if window_end is not None:
            pickup_dt = _parse_pickup(load["pickup_datetime"])
            window_ok = now <= pickup_dt <= window_end

        if (
            equip_ok
            and origin_ok
            and dest_ok
            and max_dist_ok
            and weight_ok
            and date_ok
            and window_ok
        ):
            matched_ids.add(load["load_id"])
            miles = load["miles"] or 1
            rate = load["loadboard_rate"]
            matches.append(
                SearchResultLoad(
                    **load,
                    rate_per_mile=round(rate / miles, 2),
                    deadhead_miles=round(o_dist, 1),
                    deadend_miles=round(d_dist, 1)
                    if d_dist is not None
                    else 0.0,
                    floor_rate=round(rate * (1 - target_margin), 2),
                    max_rate=round(rate * (1 + max_bump), 2),
                )
            )
            continue

        if not _alt_origin_ok(load, o_loc, alt_origin_cap):
            continue
        if not _alt_dest_ok(load, d_loc, alt_dest_cap):
            continue

        diffs: list[str] = []
        o_label = _resolved_label(o_loc)
        d_label = _resolved_label(d_loc) if d_loc else ""

        if not equip_ok:
            diffs.append(
                f"Equipment is "
                f"{_equipment_label(load['equipment_type'])}"
                f", not {_equipment_label(equip)}"
            )
        if not origin_ok:
            if o_loc.is_city:
                diffs.append(
                    f"Pickup is in {load['origin']} —"
                    f" {round(o_dist)} mi from {o_label}"
                    f" ({round(o_dist - radius_miles)} mi"
                    f" outside your"
                    f" {radius_miles}-mile radius)"
                )
            else:
                diffs.append(
                    f"Pickup is in {load['origin']} (not in {o_label})"
                )
        if not dest_ok and d_loc is not None:
            if d_loc.is_city:
                diffs.append(
                    f"Delivers to {load['destination']} —"
                    f" {round(d_dist)} mi from {d_label}"
                    f" ({round(d_dist - radius_miles)} mi"
                    f" outside your"
                    f" {radius_miles}-mile radius)"
                )
            else:
                diffs.append(
                    f"Delivers to {load['destination']} (not in {d_label})"
                )
        if not max_dist_ok:
            diffs.append(
                f"Haul distance is {load['miles']} mi"
                f" (exceeds your"
                f" {max_distance_miles}-mile max)"
            )
        if not weight_ok:
            diffs.append(
                f"Load weighs {load['weight']} lbs"
                f" (exceeds your"
                f" {max_weight}-lb max)"
            )
        if not date_ok:
            load_dt = _parse_pickup(load["pickup_datetime"])
            diffs.append(
                f"Pickup is"
                f" {load_dt.strftime('%Y-%m-%d %H:%M UTC')}"
                f", not {pickup_datetime}"
            )
        if not window_ok:
            pickup_dt = _parse_pickup(load["pickup_datetime"])
            diffs.append(
                f"Pickup is at"
                f" {pickup_dt.strftime('%Y-%m-%d %H:%M UTC')}"
                f", outside your"
                f" {pickup_window_hours}-hour window"
            )

        if not diffs:
            continue

        miles = load["miles"] or 1
        rate = load["loadboard_rate"]
        alternatives.append(
            AlternativeLoad(
                **load,
                rate_per_mile=round(rate / miles, 2),
                deadhead_miles=round(o_dist, 1),
                deadend_miles=round(d_dist, 1)
                if d_dist is not None
                else 0.0,
                floor_rate=round(rate * (1 - target_margin), 2),
                max_rate=round(rate * (1 + max_bump), 2),
                differences=diffs,
            )
        )

    # Strict matches: all share the same equipment/origin/dest hit.
    # Rank by proximity first (lower deadhead = better origin match,
    # lower deadend = better destination match), then rate, then distance.
    matches.sort(
        key=lambda m: (
            m.deadhead_miles,
            m.deadend_miles,
            -m.loadboard_rate,
            m.miles,
        )
    )

    _EXACT_THRESHOLD = 3
    _TOTAL_CAP = 5

    if len(matches) >= _EXACT_THRESHOLD:
        alternatives = []
    else:
        slots = _TOTAL_CAP - len(matches)
        # Alternatives: equipment match first, then origin proximity,
        # then destination proximity, then rate, then distance.
        alternatives.sort(
            key=lambda a: (
                int(
                    any("Equipment" in d for d in a.differences)
                ),
                a.deadhead_miles,
                a.deadend_miles,
                -a.loadboard_rate,
                a.miles,
            )
        )
        alternatives = alternatives[:slots]

    return LoadSearchResponse(
        loads=matches,
        alternative_loads=alternatives,
        origin_resolved=o_loc,
        destination_resolved=d_loc,
        radius_miles=radius_miles,
        total_found=len(matches),
        total_alternatives=len(alternatives),
    )


async def search_loads_by_lane(
    origin: str,
    destination: str,
    radius_miles: int = 75,
) -> LoadSearchResponse:
    o_loc = await resolve_location(origin)
    d_loc = await resolve_location(destination)

    ns = get_all_settings()
    target_margin = ns.get("target_margin", 0.15)
    max_bump = ns.get("max_bump_above_loadboard", 0.03)

    matches: list[SearchResultLoad] = []

    for load in get_all_loads():
        origin_ok, o_dist = _origin_ok(load, o_loc, radius_miles)
        dest_ok, d_dist = _dest_ok(load, d_loc, radius_miles)

        if not (origin_ok and dest_ok):
            continue

        miles = load["miles"] or 1
        rate = load["loadboard_rate"]
        matches.append(
            SearchResultLoad(
                **load,
                rate_per_mile=round(rate / miles, 2),
                deadhead_miles=round(o_dist, 1),
                deadend_miles=round(d_dist, 1) if d_dist is not None else 0.0,
                floor_rate=round(rate * (1 - target_margin), 2),
                max_rate=round(rate * (1 + max_bump), 2),
            )
        )

    matches.sort(key=lambda m: (m.deadhead_miles, m.deadend_miles, -m.loadboard_rate, m.miles))

    return LoadSearchResponse(
        loads=matches,
        alternative_loads=[],
        origin_resolved=o_loc,
        destination_resolved=d_loc,
        radius_miles=radius_miles,
        total_found=len(matches),
        total_alternatives=0,
    )


def get_load(load_id: str) -> Load | None:
    load = get_load_by_id(load_id)
    return Load(**load) if load else None


_RESCHEDULE_TOLERANCE_HOURS = 6.0


def check_pickup_reschedule(
    req: PickupRescheduleRequest,
) -> tuple[PickupRescheduleResponse | None, str | None]:
    load = get_load_by_id(req.load_id)
    if not load:
        return None, f"Load {req.load_id} not found"

    current_dt = _parse_pickup(load["pickup_datetime"])
    now = datetime.now(timezone.utc)

    if req.new_pickup_datetime is not None:
        requested_dt = _parse_pickup(req.new_pickup_datetime)
    else:
        requested_dt = now + timedelta(hours=req.new_pickup_window)

    diff_secs = (requested_dt - current_dt).total_seconds()
    diff_hours = round(abs(diff_secs) / 3600, 1)
    direction = "later" if diff_secs > 0 else "earlier"
    approved = diff_hours <= _RESCHEDULE_TOLERANCE_HOURS

    if approved:
        reason = (
            f"Approved — {diff_hours}h {direction} is within"
            f" the {_RESCHEDULE_TOLERANCE_HOURS}h tolerance"
        )
    else:
        reason = (
            f"Denied — {diff_hours}h {direction} exceeds"
            f" the {_RESCHEDULE_TOLERANCE_HOURS}h tolerance"
        )

    fmt = "%Y-%m-%dT%H:%M:%S"
    return PickupRescheduleResponse(
        load_id=req.load_id,
        approved=approved,
        current_pickup_datetime=current_dt.strftime(fmt),
        requested_pickup_datetime=requested_dt.strftime(fmt),
        difference_hours=diff_hours,
        reason=reason,
    ), None
