from fastapi import APIRouter, HTTPException, Security

from app.config import get_settings
from app.models.load import (
    LaneSearchRequest,
    Load,
    LoadSearchRequest,
    LoadSearchResponse,
    PickupRescheduleRequest,
    PickupRescheduleResponse,
)
from app.routes._auth import verify_api_key
from app.services.load_service import (
    check_pickup_reschedule,
    get_load,
    search_loads,
    search_loads_by_lane,
)

router = APIRouter(prefix="/api/loads", tags=["Loads"])


@router.post(
    "/search",
    response_model=LoadSearchResponse,
    dependencies=[Security(verify_api_key)],
)
async def search_loads_route(body: LoadSearchRequest):
    """
    Load search by origin and destination.
    Origin/destination accept: city name, state (TX/Texas), or region (South Central).
    Equipment type required; destination optional.
    """
    radius = body.radius_miles or get_settings().default_search_radius_miles
    try:
        return await search_loads(
            origin=body.origin,
            equipment_type=body.equipment_type,
            destination=body.destination,
            pickup_datetime=body.pickup_datetime,
            radius_miles=radius,
            pickup_window_hours=body.pickup_window_hours,
            max_distance_miles=body.max_distance_miles,
            max_weight=body.max_weight,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post(
    "/search/lane",
    response_model=LoadSearchResponse,
    dependencies=[Security(verify_api_key)],
)
async def search_loads_by_lane_route(body: LaneSearchRequest):
    """
    Strict lane search by origin and destination only.
    Returns all loads that match both origin and destination within the default
    search radius. No equipment, date, or weight filters applied.
    """
    radius = get_settings().default_search_radius_miles
    try:
        return await search_loads_by_lane(
            origin=body.origin,
            destination=body.destination,
            radius_miles=radius,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post(
    "/reschedule",
    response_model=PickupRescheduleResponse,
    dependencies=[Security(verify_api_key)],
)
async def reschedule_pickup_route(body: PickupRescheduleRequest):
    """
    Simulate shipper response to a pickup reschedule request.
    Approved if the requested time is within 6 hours of the
    current pickup. Provide new_pickup_datetime (ISO 8601) or
    new_pickup_window (hours from now).
    """
    result, error = check_pickup_reschedule(body)
    if error:
        raise HTTPException(404, error)
    return result


@router.get(
    "/{load_id}",
    response_model=Load,
    dependencies=[Security(verify_api_key)],
)
async def get_load_route(load_id: str):
    """Get single load by ID."""
    load = get_load(load_id)
    if not load:
        raise HTTPException(404, f"Load {load_id} not found")
    return load
