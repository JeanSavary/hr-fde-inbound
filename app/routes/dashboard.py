from fastapi import APIRouter, Security
from app.models.dashboard import DashboardMetrics
from app.services.dashboard_service import get_dashboard_metrics
from app.routes._auth import verify_api_key

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "/metrics",
    response_model=DashboardMetrics,
    dependencies=[Security(verify_api_key)],
    include_in_schema=False,
)
async def dashboard_metrics():
    """Aggregated metrics for the operational dashboard."""
    return get_dashboard_metrics()
