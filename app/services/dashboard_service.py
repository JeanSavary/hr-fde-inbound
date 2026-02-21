from app.models.dashboard import DashboardMetrics
from app.db.repositories.dashboard_repo import get_dashboard_data


def get_dashboard_metrics() -> DashboardMetrics:
    return DashboardMetrics(**get_dashboard_data())
