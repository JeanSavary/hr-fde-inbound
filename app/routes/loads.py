from fastapi import APIRouter, HTTPException, Security, Query

from app.config import get_settings
from app.models.load import Load, LoadSearchResponse
from app.routes._auth import verify_api_key
from app.services.load_service import get_load, search_loads

router = APIRouter(prefix="/api/loads", tags=["Loads"])


@router.get(
    "/search",
    response_model=LoadSearchResponse,
    dependencies=[Security(verify_api_key)],
)
async def search_loads_route(
    origin: str = Query(..., description="Origin city/area"),
    equipment_type: str = Query(
        ..., description="dry_van, reefer, flatbed, step_deck, power_only"
    ),
    destination: str | None = Query(None, description="Destination city/area"),
    pickup_date: str | None = Query(None, description="YYYY-MM-DD"),
    radius_miles: int | None = Query(
        None, description="Search radius in miles (default 75)"
    ),
    pickup_window_hours: int | None = Query(
        None,
        description="Only loads picking up within this many hours from now",
    ),
    max_distance_miles: int | None = Query(
        None, description="Maximum haul distance in miles"
    ),
):
    """
    Load search by origin and destination.
    Origin/destination accept: city name, state (TX/Texas), or region (South Central).
    Equipment type required; destination optional.
    """
    radius = radius_miles or get_settings().default_search_radius_miles
    try:
        return await search_loads(
            origin=origin,
            equipment_type=equipment_type,
            destination=destination,
            pickup_date=pickup_date,
            radius_miles=radius,
            pickup_window_hours=pickup_window_hours,
            max_distance_miles=max_distance_miles,
        )
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get(
    "/{load_id}", response_model=Load, dependencies=[Security(verify_api_key)]
)
async def get_load_route(load_id: str):
    """Get single load by ID."""
    load = get_load(load_id)
    if not load:
        raise HTTPException(404, f"Load {load_id} not found")
    return load
