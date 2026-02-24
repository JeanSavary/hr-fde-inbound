from datetime import datetime, timedelta, timezone

from app.models.enums import Verdict
from app.models.offer import (
    OfferCreateRequest,
    OfferResponse,
    OfferAnalysisRequest,
    OfferAnalysisResponse,
)
from app.db.repositories.load_repo import get_load_by_id
from app.db.repositories.offer_repo import insert_offer
from app.utils.fmcsa import ensure_mc_prefix

# ── Broker strategy thresholds ──────────────────────────
_RATE_REJECT_MULTIPLIER = 1.20
_PICKUP_ACCEPT_HOURS = 12
_PICKUP_REJECT_HOURS = 48
_MILES_COUNTER_TOLERANCE = 0.20


def _parse_dt(dt_str: str) -> datetime:
    dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def analyze_offer(
    req: OfferAnalysisRequest,
    rate_floor_pct: float,
    rate_ceiling_pct: float,
) -> tuple[OfferAnalysisResponse, None] | tuple[None, str]:
    load = get_load_by_id(req.load_id)
    if not load:
        return None, f"Load {req.load_id} not found"
    if load.get("status") == "booked":
        return None, f"Load {req.load_id} is already booked"

    rejects: list[str] = []
    counters: list[str] = []
    accepts: dict[str, str] = {}

    # ── Miles (priority 1) ───────────────────────────
    if req.asking_radius_miles is not None:
        load_miles = load["miles"]
        over = load_miles - req.asking_radius_miles
        tolerance = int(req.asking_radius_miles * _MILES_COUNTER_TOLERANCE)
        counter_max = req.asking_radius_miles + tolerance

        if load_miles <= req.asking_radius_miles:
            accepts["radius_miles"] = (
                f"Haul is {load_miles} mi, within"
                f" your {req.asking_radius_miles} mi"
                f" max"
            )
        elif load_miles <= counter_max:
            counters.append(
                f"Miles: haul is {load_miles} mi"
                f" ({over} mi over your"
                f" {req.asking_radius_miles} mi max)"
            )
        else:
            rejects.append(
                f"Haul is {load_miles} mi — {over} mi"
                f" over your"
                f" {req.asking_radius_miles} mi max"
            )

    # ── Pickup datetime (priority 2) ──────────────────
    if req.asking_pickup_datetime is not None:
        load_pickup = _parse_dt(load["pickup_datetime"])
        try:
            ask_date = _parse_dt(req.asking_pickup_datetime)
        except (ValueError, TypeError):
            ask_date = _parse_dt(req.asking_pickup_datetime + "T00:00:00Z")
        secs = (ask_date - load_pickup).total_seconds()
        hours_off = round(abs(secs) / 3600, 1)
        direction = "later" if secs > 0 else "earlier"
        fmt = "%Y-%m-%d %H:%M UTC"

        if hours_off <= _PICKUP_ACCEPT_HOURS:
            accepts["pickup_datetime"] = (
                f"Pickup on"
                f" {load_pickup.strftime(fmt)}"
                f" works ({hours_off}h {direction}"
                f" from your ask)"
            )
        elif hours_off <= _PICKUP_REJECT_HOURS:
            counters.append(
                f"Pickup datetime: scheduled"
                f" {load_pickup.strftime(fmt)},"
                f" your ask is {hours_off}h"
                f" {direction}"
            )
        else:
            rejects.append(
                f"Pickup is {hours_off}h {direction}"
                f" than scheduled — incompatible"
            )

    # ── Pickup window (priority 3) ───────────────────
    if req.asking_pickup_window_hours is not None:
        now = datetime.now(timezone.utc)
        load_pickup = _parse_dt(load["pickup_datetime"])
        wh = req.asking_pickup_window_hours
        window_end = now + timedelta(hours=wh)
        double_end = now + timedelta(hours=wh * 2)
        hours_until = round(
            (load_pickup - now).total_seconds() / 3600,
            1,
        )
        fmt = "%Y-%m-%d %H:%M UTC"

        if load_pickup < now:
            rejects.append("Pickup time has already passed")
        elif load_pickup <= window_end:
            accepts["pickup_window"] = (
                f"Pickup in {hours_until}h"
                f" ({load_pickup.strftime(fmt)}),"
                f" within your {wh}h window"
            )
        elif load_pickup <= double_end:
            counters.append(
                f"Pickup window: load picks up in"
                f" {hours_until}h"
                f" ({load_pickup.strftime(fmt)}),"
                f" outside your {wh}h window"
            )
        else:
            rejects.append(
                f"Pickup is {hours_until}h away — well beyond {wh}h window"
            )

    # ── Rate (priority 4) ────────────────────────────
    if req.asking_rate is not None:
        original = load["loadboard_rate"]
        ceiling = round(original * rate_ceiling_pct, 2)
        reject_line = round(original * _RATE_REJECT_MULTIPLIER, 2)
        pct = (
            round(
                ((req.asking_rate - original) / original) * 100,
                1,
            )
            if original
            else 0
        )

        if req.asking_rate <= ceiling:
            accepts["rate"] = (
                f"${req.asking_rate:.2f} is within"
                f" our range (loadboard"
                f" ${original:.2f})"
            )
        elif req.asking_rate <= reject_line:
            counters.append(
                f"Rate: we can do ${ceiling:.2f}"
                f" (your ask ${req.asking_rate:.2f}"
                f" is {pct:+.1f}% vs loadboard)"
            )
        else:
            rejects.append(
                f"Rate ${req.asking_rate:.2f} is"
                f" {pct:+.1f}% vs loadboard"
                f" — too far from our"
                f" ${ceiling:.2f} ceiling"
            )

    # ── Build response ───────────────────────────────
    if rejects:
        return OfferAnalysisResponse(
            load_id=req.load_id,
            verdict=Verdict.REJECT,
            reason="; ".join(rejects),
        ), None

    if counters:
        return OfferAnalysisResponse(
            load_id=req.load_id,
            verdict=Verdict.COUNTER,
            counter_offers=counters,
        ), None

    priority = [
        "radius_miles",
        "pickup_datetime",
        "pickup_window",
        "rate",
    ]
    accept_reason = next(
        (accepts[k] for k in priority if k in accepts),
        None,
    )
    return OfferAnalysisResponse(
        load_id=req.load_id,
        verdict=Verdict.ACCEPT,
        reason=accept_reason,
    ), None


def create_offer(
    req: OfferCreateRequest,
    rate_floor_percent: float,
    rate_ceiling_percent: float,
) -> tuple[OfferResponse, None] | tuple[None, str]:
    load = get_load_by_id(req.load_id)
    if not load:
        return None, f"Load {req.load_id} not found"

    original_rate = load["loadboard_rate"]
    floor = round(original_rate * rate_floor_percent, 2)
    ceiling = round(original_rate * rate_ceiling_percent, 2)

    rate_diff = round(req.offer_amount - original_rate, 2)
    if original_rate:
        rate_diff_pct = round((rate_diff / original_rate) * 100, 2)
    else:
        rate_diff_pct = 0.0

    agreed_pickup = req.agreed_pickup_datetime
    orig_pickup = load["pickup_datetime"]
    pickup_changed = agreed_pickup is not None and agreed_pickup != orig_pickup

    result = insert_offer(
        {
            "call_id": req.call_id,
            "load_id": req.load_id,
            "mc_number": ensure_mc_prefix(req.mc_number),
            "offer_amount": req.offer_amount,
            "offer_type": req.offer_type.value,
            "round_number": req.round_number,
            "status": req.status.value,
            "notes": req.notes,
            "original_rate": original_rate,
            "rate_difference": rate_diff,
            "rate_difference_pct": rate_diff_pct,
            "original_pickup_datetime": orig_pickup,
            "agreed_pickup_datetime": agreed_pickup,
            "pickup_changed": pickup_changed,
        }
    )

    return OfferResponse(
        offer_id=result["offer_id"],
        call_id=result.get("call_id"),
        load_id=result["load_id"],
        mc_number=result["mc_number"],
        offer_amount=result["offer_amount"],
        offer_type=req.offer_type,
        round_number=result["round_number"],
        status=req.status,
        notes=result.get("notes", ""),
        created_at=result["created_at"],
        rate_floor=floor,
        rate_ceiling=ceiling,
        original_rate=original_rate,
        rate_difference=rate_diff,
        rate_difference_pct=rate_diff_pct,
        original_pickup_datetime=orig_pickup,
        agreed_pickup_datetime=agreed_pickup,
        pickup_changed=pickup_changed,
    ), None
