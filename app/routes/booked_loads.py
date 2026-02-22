from fastapi import APIRouter, HTTPException, Security

from app.models.offer import BookedLoadRequest, BookedLoadResponse
from app.services.booked_load_service import (
    book_load,
    get_booking,
    list_bookings,
)
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/booked-loads", tags=["Booked Loads"])


@router.post(
    "",
    response_model=BookedLoadResponse,
    dependencies=[Security(verify_api_key)],
)
async def create_booking(req: BookedLoadRequest):
    """
    Confirm a load is booked by a carrier. Marks the load as unavailable
    so it won't appear in future searches.
    """
    result, error = book_load(req)
    if error:
        status = 409 if "already booked" in error else 404
        raise HTTPException(status, error)
    return result


@router.get(
    "",
    response_model=list[BookedLoadResponse],
    dependencies=[Security(verify_api_key)],
)
async def list_all_bookings():
    """List all confirmed bookings."""
    return list_bookings()


@router.get(
    "/{load_id}",
    response_model=BookedLoadResponse,
    dependencies=[Security(verify_api_key)],
)
async def get_load_booking(load_id: str):
    """Get booking details for a specific load."""
    booking = get_booking(load_id)
    if not booking:
        raise HTTPException(404, f"No booking found for load {load_id}")
    return booking
