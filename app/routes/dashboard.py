from fastapi import APIRouter, Query, Security
from app.models.dashboard import DashboardMetrics
from app.services.dashboard_service import get_dashboard_metrics
from app.routes._auth import verify_api_key
from app.utils.period import Period

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get(
    "/metrics",
    response_model=DashboardMetrics,
    dependencies=[Security(verify_api_key)],
    include_in_schema=True,
)
async def dashboard_metrics(
    period: Period = Query(Period.last_month),
):
    """Aggregated metrics for the operational dashboard."""
    return get_dashboard_metrics(period=period.value)
