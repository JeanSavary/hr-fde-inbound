"""
Geolocation utilities — in-memory lookup first, Nominatim fallback for unknowns.
City resolution: alias → exact → prefix → fuzzy → geocode API.
"""

import logging
import math

import httpx
from cachetools import TTLCache
from rapidfuzz import fuzz, process

from app.db.city_data import (
    CITY_ALIASES,
    CITY_COORDS,
    REGION_ALIASES,
    STATE_NAMES,
    STATE_TO_REGION,
    get_coords,
)

log = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_geocode_cache: TTLCache = TTLCache(maxsize=512, ttl=86400)  # 24h

_ALL_CITY_KEYS = list(CITY_COORDS.keys())


def _resolve_city_static(cleaned: str) -> tuple[str, float, float] | None:
    """In-memory lookup only. Returns (canonical_name, lat, lng) or None."""
    if cleaned in CITY_ALIASES:
        canonical = CITY_ALIASES[cleaned]
        lat, lng = get_coords(canonical)
        return canonical, lat, lng
    if cleaned in CITY_COORDS:
        lat, lng = get_coords(cleaned)
        return cleaned, lat, lng
    if "," not in cleaned:
        candidates = [k for k in _ALL_CITY_KEYS if k.startswith(cleaned + ",")]
        if len(candidates) == 1:
            lat, lng = get_coords(candidates[0])
            return candidates[0], lat, lng
    match = process.extractOne(
        cleaned, _ALL_CITY_KEYS, scorer=fuzz.WRatio, score_cutoff=70
    )
    if match:
        city_key, _score, _idx = match
        lat, lng = get_coords(city_key)
        return city_key, lat, lng
    return None


async def _geocode_city(query: str) -> tuple[str, float, float] | None:
    """Fallback: call Nominatim API. Cached 24h."""
    if query in _geocode_cache:
        return _geocode_cache[query]
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": f"{query}, USA",
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "us",
                },
                headers={"User-Agent": "HappyRobots-CarrierAPI/1.0"},
            )
            if resp.status_code != 200:
                return None
            data = resp.json()
            if not data:
                return None
            r = data[0]
            name = r.get("display_name", query)
            lat = float(r["lat"])
            lon = float(r["lon"])
            result = (name, lat, lon)
            _geocode_cache[query] = result
            log.debug("Geocoded '%s' -> %s", query, name)
            return result
    except Exception as exc:
        log.warning("Geocode failed for '%s': %s", query, exc)
        return None


def _resolve_state(cleaned: str) -> str | None:
    """Resolve input to state abbreviation (TX, CA, etc.) or None."""
    cleaned = cleaned.strip().lower()
    if len(cleaned) == 2:
        abbrev = cleaned.upper()
        if abbrev in STATE_TO_REGION:
            return abbrev
    return STATE_NAMES.get(cleaned)


def _resolve_region(cleaned: str) -> str | None:
    """Resolve input to canonical region name or None."""
    cleaned = cleaned.strip().lower()
    return REGION_ALIASES.get(cleaned)


async def resolve_location(raw_input: str) -> tuple[str, object]:
    """
    Resolve origin/destination to city, state, or region.

    Returns:
      ("city", (name, lat, lng))   — use haversine distance filtering
      ("state", state_abbrev)      — filter loads by state (e.g. "TX")
      ("region", region_name)      — filter loads by region (e.g. "South Central")

    Raises ValueError if input cannot be resolved.
    """
    if not raw_input or not raw_input.strip():
        raise ValueError("Empty location input")

    cleaned = raw_input.lower().strip()
    for prefix in (
        "near ",
        "around ",
        "outside ",
        "just outside ",
        "the ",
        "in ",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
    for suffix in (" area", " metro", " region", " metropolitan"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    cleaned = cleaned.strip()

    # 1. Try state (2-letter or full name) — before city to avoid "in" matching "indianapolis"
    state = _resolve_state(cleaned)
    if state:
        return ("state", state)

    # 2. Try region
    region = _resolve_region(cleaned)
    if region:
        return ("region", region)

    # 3. Try city (includes alias, fuzzy, Nominatim)
    city_result = _resolve_city_static(cleaned)
    if city_result:
        return ("city", city_result)
    geocode = await _geocode_city(raw_input.strip())
    if geocode:
        return ("city", geocode)

    raise ValueError(f"Could not resolve location: '{raw_input}'")


async def resolve_city(raw_input: str) -> tuple[str, float, float] | None:
    """
    Resolve free-text city name to (canonical_name, lat, lng).
    Alias → exact → prefix → fuzzy (in-memory) → Nominatim API (fallback).
    """
    if not raw_input or not raw_input.strip():
        return None

    cleaned = raw_input.lower().strip()
    for prefix in (
        "near ",
        "around ",
        "outside ",
        "just outside ",
        "the ",
        "in ",
    ):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
    for suffix in (" area", " metro", " region", " metropolitan"):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
    cleaned = cleaned.strip()

    result = _resolve_city_static(cleaned)
    if result is not None:
        return result

    return await _geocode_city(raw_input.strip())


def haversine_miles(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance between two points in miles."""
    R = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return R * 2 * math.asin(math.sqrt(a))
