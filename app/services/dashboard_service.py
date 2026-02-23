from datetime import date, timedelta
from app.db.repositories.dashboard_repo import (
    get_calls_since,
    get_bookings_with_loads_since,
    get_offers_for_calls,
)
from app.models.dashboard import DashboardMetrics, FunnelStage, RateIntelligence, RecentCall


# ── Period helpers ───────────────────────────────────────────────────────────

_PERIOD_DAYS = {
    "today": 1,
    "last_week": 7,
    "last_month": 30,
    "all_time": None,
}


def _period_range(period: str) -> tuple[str | None, str | None]:
    """Return (current_since, previous_since) ISO date strings."""
    days = _PERIOD_DAYS.get(period)
    if days is None:
        return None, None  # all_time: no filter, no trend
    today = date.today()
    if period == "today":
        current_since = today.isoformat()
        previous_since = (today - timedelta(days=1)).isoformat()
    else:
        current_since = (today - timedelta(days=days - 1)).isoformat()
        previous_since = (today - timedelta(days=2 * days - 1)).isoformat()
    return current_since, previous_since


def _filter_before(rows: list[dict], cutoff: str) -> list[dict]:
    """Keep rows with created_at < cutoff."""
    return [r for r in rows if r.get("created_at", "") < cutoff]


# ── Trend helpers ────────────────────────────────────────────────────────────

def _compute_trend(current: float, previous: float) -> str | None:
    if previous == 0:
        return None
    change = ((current - previous) / previous) * 100
    sign = "+" if change >= 0 else ""
    return f"{sign}{round(change, 1)}%"


def _compute_conversion_trend(current: float, previous: float) -> str | None:
    if previous == 0 and current == 0:
        return None
    diff = current - previous
    sign = "+" if diff >= 0 else ""
    return f"{sign}{round(diff, 1)}%"


# ── Funnel ───────────────────────────────────────────────────────────────────

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


# ── Rate intelligence ────────────────────────────────────────────────────────

def _build_rate_intelligence(bookings: list[dict]) -> RateIntelligence:
    if not bookings:
        return RateIntelligence()

    loadboard_rates = [b["loadboard_rate"] for b in bookings if b.get("loadboard_rate")]
    agreed_rates = [b["agreed_rate"] for b in bookings if b.get("agreed_rate")]

    if not loadboard_rates or not agreed_rates:
        return RateIntelligence()

    avg_lb = round(sum(loadboard_rates) / len(loadboard_rates), 2)
    avg_agreed = round(sum(agreed_rates) / len(agreed_rates), 2)
    discount = round(((avg_lb - avg_agreed) / avg_lb) * 100, 1) if avg_lb > 0 else None

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


# ── Aggregate metrics from a set of calls ────────────────────────────────────

def _trim_recent_calls(calls: list[dict]) -> list[RecentCall]:
    return [
        RecentCall(
            call_id=c["call_id"],
            mc_number=c.get("mc_number"),
            carrier_name=c.get("carrier_name"),
            lane_origin=c.get("lane_origin"),
            lane_destination=c.get("lane_destination"),
            load_id=c.get("load_id"),
            outcome=c["outcome"],
            final_rate=c.get("final_rate"),
            created_at=c["created_at"],
        )
        for c in calls[:10]
    ]


def _aggregate_calls(calls: list[dict]) -> dict:
    total = len(calls)
    if total == 0:
        return {
            "total_calls": 0,
            "calls_by_outcome": {},
            "sentiment_distribution": {},
            "booking_rate_percent": 0.0,
            "avg_rate_differential_percent": None,
            "total_revenue": 0.0,
            "recent_calls": [],
        }

    outcomes: dict[str, int] = {}
    sentiments: dict[str, int] = {}
    for c in calls:
        outcomes[c["outcome"]] = outcomes.get(c["outcome"], 0) + 1
        sentiments[c["sentiment"]] = sentiments.get(c["sentiment"], 0) + 1

    booked_calls = [c for c in calls if c["outcome"] == "booked"]
    booked = len(booked_calls)
    booking_rate = (booked / total * 100) if total else 0.0

    diffs = []
    for c in booked_calls:
        if c["initial_rate"] and c["final_rate"] and c["initial_rate"] > 0:
            diffs.append(((c["final_rate"] - c["initial_rate"]) / c["initial_rate"]) * 100)
    avg_diff = sum(diffs) / len(diffs) if diffs else None

    total_rev = sum(c["final_rate"] for c in booked_calls if c["final_rate"]) or 0.0

    return {
        "total_calls": total,
        "calls_by_outcome": outcomes,
        "sentiment_distribution": sentiments,
        "booking_rate_percent": round(booking_rate, 1),
        "avg_rate_differential_percent": round(avg_diff, 1) if avg_diff else None,
        "total_revenue": round(total_rev, 2),
        "recent_calls": _trim_recent_calls(calls),
    }


# ── Public entry point ───────────────────────────────────────────────────────

def get_dashboard_metrics(period: str = "today") -> DashboardMetrics:
    current_since, previous_since = _period_range(period)

    # Fetch current period data
    current_calls = get_calls_since(current_since)
    current_bookings = get_bookings_with_loads_since(current_since)

    # Fetch previous period data for trends
    if previous_since and current_since:
        all_since_prev = get_calls_since(previous_since)
        prev_calls = _filter_before(all_since_prev, current_since)
        all_bookings_prev = get_bookings_with_loads_since(previous_since)
        prev_bookings = _filter_before(all_bookings_prev, current_since)
    else:
        prev_calls = []
        prev_bookings = []

    # Base aggregate metrics for the period
    base_data = _aggregate_calls(current_calls)

    # Fetch offers for funnel computation
    call_ids = [c["call_id"] for c in current_calls]
    period_offers = get_offers_for_calls(call_ids)

    # KPIs: current period
    n_calls = len(current_calls)
    n_calls_prev = len(prev_calls)

    n_booked = len([c for c in current_calls if c["outcome"] == "booked"])
    n_booked_prev = len([c for c in prev_calls if c["outcome"] == "booked"])

    revenue = sum(b.get("agreed_rate", 0) for b in current_bookings)
    revenue_prev = sum(b.get("agreed_rate", 0) for b in prev_bookings)

    conversion = round((n_booked / n_calls) * 100, 1) if n_calls > 0 else 0
    conversion_prev = round((n_booked_prev / n_calls_prev) * 100, 1) if n_calls_prev > 0 else 0

    pending_transfer = len([c for c in current_calls if c["outcome"] == "transferred_to_ops"])

    # Funnel for the period
    funnel = _build_funnel(current_calls, period_offers)

    # Rate intelligence for the period
    rate_intel = _build_rate_intelligence(current_bookings)

    # Trends (None for all_time)
    has_trend = previous_since is not None

    base_data.update({
        "period": period,
        "calls_today": n_calls,
        "calls_trend": _compute_trend(n_calls, n_calls_prev) if has_trend else None,
        "booked_today": n_booked,
        "booked_trend": _compute_trend(n_booked, n_booked_prev) if has_trend else None,
        "revenue_today": round(revenue, 2),
        "revenue_trend": _compute_trend(revenue, revenue_prev) if has_trend else None,
        "conversion_rate": conversion,
        "conversion_trend": _compute_conversion_trend(conversion, conversion_prev) if has_trend else None,
        "pending_transfer": pending_transfer,
        "funnel_data": funnel,
        "rate_intelligence": rate_intel,
    })

    return DashboardMetrics(**base_data)
