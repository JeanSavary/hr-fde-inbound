from datetime import date, timedelta
from app.db.repositories.dashboard_repo import (
    get_dashboard_data,
    get_calls_by_date,
    get_bookings_with_loads_by_date,
    get_all_bookings_with_loads,
    get_offers_for_calls,
)
from app.models.dashboard import DashboardMetrics, FunnelStage, RateIntelligence


def _compute_trend(today_val: float, yesterday_val: float) -> str | None:
    if yesterday_val == 0:
        return None
    change = ((today_val - yesterday_val) / yesterday_val) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{round(change, 1)}%"


def _compute_conversion_trend(today_rate: float, yesterday_rate: float) -> str | None:
    """For conversion rate, trend is the absolute difference."""
    if yesterday_rate == 0 and today_rate == 0:
        return None
    diff = today_rate - yesterday_rate
    sign = "+" if diff >= 0 else ""
    return f"{sign}{round(diff, 1)}%"


def _build_funnel(calls: list[dict], offers: list[dict]) -> list[FunnelStage]:
    total = len(calls)
    if total == 0:
        return []

    authenticated = [c for c in calls if c["outcome"] != "invalid_carrier"]
    load_matched = [c for c in authenticated if c["outcome"] != "no_loads_available"]

    call_ids_with_offers = {o["call_id"] for o in offers if o.get("call_id")}
    offer_made = [c for c in load_matched if c["call_id"] in call_ids_with_offers]

    negotiated = [c for c in offer_made if (c.get("negotiation_rounds") or 0) >= 1]
    booked = [c for c in negotiated if c["outcome"] == "booked"]

    stages = [
        ("Inbound Calls", total),
        ("Authenticated", len(authenticated)),
        ("Load Matched", len(load_matched)),
        ("Offer Made", len(offer_made)),
        ("Negotiated", len(negotiated)),
        ("Booked", len(booked)),
    ]

    return [
        FunnelStage(stage=name, count=count, pct=round(count / total * 100))
        for name, count in stages
    ]


def _build_rate_intelligence(bookings: list[dict]) -> RateIntelligence | None:
    if not bookings:
        return RateIntelligence()

    loadboard_rates = [b["loadboard_rate"] for b in bookings if b.get("loadboard_rate")]
    agreed_rates = [b["agreed_rate"] for b in bookings if b.get("agreed_rate")]

    if not loadboard_rates or not agreed_rates:
        return RateIntelligence()

    avg_lb = round(sum(loadboard_rates) / len(loadboard_rates), 2)
    avg_agreed = round(sum(agreed_rates) / len(agreed_rates), 2)
    discount = round(((avg_lb - avg_agreed) / avg_lb) * 100, 1) if avg_lb > 0 else None

    # margin_pct: average of per-booking margins
    per_booking_margins = []
    for b in bookings:
        lb = b.get("loadboard_rate")
        ag = b.get("agreed_rate")
        if lb and ag and lb > 0:
            per_booking_margins.append(((lb - ag) / lb) * 100)
    avg_margin = round(sum(per_booking_margins) / len(per_booking_margins), 1) if per_booking_margins else None

    return RateIntelligence(
        avg_loadboard=avg_lb,
        avg_agreed=avg_agreed,
        discount_pct=discount,
        margin_pct=avg_margin,
    )


def get_dashboard_metrics() -> DashboardMetrics:
    # Get existing aggregate metrics
    base_data = get_dashboard_data()

    # Get daily data
    today_str = date.today().isoformat()
    yesterday_str = (date.today() - timedelta(days=1)).isoformat()

    calls_today = get_calls_by_date(today_str)
    calls_yesterday = get_calls_by_date(yesterday_str)

    bookings_today = get_bookings_with_loads_by_date(today_str)
    bookings_yesterday = get_bookings_with_loads_by_date(yesterday_str)

    # Daily KPIs
    n_calls_today = len(calls_today)
    n_calls_yesterday = len(calls_yesterday)

    n_booked_today = len([c for c in calls_today if c["outcome"] == "booked"])
    n_booked_yesterday = len([c for c in calls_yesterday if c["outcome"] == "booked"])

    revenue_today = sum(b.get("agreed_rate", 0) for b in bookings_today)
    revenue_yesterday = sum(b.get("agreed_rate", 0) for b in bookings_yesterday)

    conversion_rate = round((n_booked_today / n_calls_today) * 100, 1) if n_calls_today > 0 else 0
    conversion_yesterday = round((n_booked_yesterday / n_calls_yesterday) * 100, 1) if n_calls_yesterday > 0 else 0

    pending_transfer = len([c for c in calls_today if c["outcome"] == "transferred_to_ops"])

    # Funnel
    today_call_ids = [c["call_id"] for c in calls_today]
    today_offers = get_offers_for_calls(today_call_ids)
    funnel = _build_funnel(calls_today, today_offers)

    # Rate intelligence (all bookings, not just today)
    all_bookings = get_all_bookings_with_loads()
    rate_intel = _build_rate_intelligence(all_bookings)

    # Merge everything
    base_data.update({
        "calls_today": n_calls_today,
        "calls_trend": _compute_trend(n_calls_today, n_calls_yesterday),
        "booked_today": n_booked_today,
        "booked_trend": _compute_trend(n_booked_today, n_booked_yesterday),
        "revenue_today": round(revenue_today, 2),
        "revenue_trend": _compute_trend(revenue_today, revenue_yesterday),
        "conversion_rate": conversion_rate,
        "conversion_trend": _compute_conversion_trend(conversion_rate, conversion_yesterday),
        "pending_transfer": pending_transfer,
        "funnel_data": funnel,
        "rate_intelligence": rate_intel,
    })

    return DashboardMetrics(**base_data)
