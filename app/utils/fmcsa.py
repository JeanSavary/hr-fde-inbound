"""
FMCSA SAFER lookup. Uses real API if FMCSA_WEB_KEY is set,
otherwise returns realistic mock data for the demo.
"""

import asyncio
import logging
import re

import httpx
from cachetools import TTLCache

from app.models.carrier import FMCSACarrier

log = logging.getLogger(__name__)

FMCSA_BASE = "https://mobile.fmcsa.dot.gov/qc/services/carriers/docket-number"

_RETRY_ATTEMPTS = 2
_RETRY_INITIAL_DELAY = 1.0  # seconds
_RETRY_BACKOFF = 2.0
_RETRY_MAX_DELAY = 100.0

# Keyed by (mc, web_key) so mock and live results stay separate
_fmcsa_cache: TTLCache = TTLCache(maxsize=512, ttl=3600)

_WORD_DIGITS = {
    "zero": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
}


def normalize_mc(raw: str) -> str:
    """
    Accept any format: MC-123456, MC 123456, mc123456, 123456,
    'one two three four five six'. Returns digits only.
    """
    text = raw.lower().strip()
    for word, digit in _WORD_DIGITS.items():
        text = text.replace(word, digit)
    return re.sub(r"[^\d]", "", text)


async def lookup_fmcsa(mc_number: str, web_key: str = "") -> FMCSACarrier:
    mc = normalize_mc(mc_number)

    if not mc:
        return FMCSACarrier(
            mc_number=mc_number,
            legal_name="UNKNOWN",
            status="NOT_FOUND",
            authority_status="N",
        )

    cache_key = (mc, bool(web_key))
    if cache_key in _fmcsa_cache:
        log.debug("FMCSA cache hit for MC %s", mc)
        return _fmcsa_cache[cache_key]

    if web_key:
        url = f"{FMCSA_BASE}/{mc}?webKey={web_key}"
        delay = _RETRY_INITIAL_DELAY
        async with httpx.AsyncClient(timeout=5.0) as client:
            for attempt in range(1, _RETRY_ATTEMPTS + 1):
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("content", [])
                        if not content:
                            break
                        carrier = content[0].get("carrier", {})
                        result = _parse_carrier(mc, carrier)
                        _fmcsa_cache[cache_key] = result
                        return result
                    log.warning(
                        "FMCSA attempt %d/%d: HTTP %d",
                        attempt,
                        _RETRY_ATTEMPTS,
                        resp.status_code,
                    )
                except Exception as exc:
                    log.warning(
                        "FMCSA attempt %d/%d failed: %s",
                        attempt,
                        _RETRY_ATTEMPTS,
                        exc,
                    )
                if attempt < _RETRY_ATTEMPTS:
                    await asyncio.sleep(delay)
                    delay = min(delay * _RETRY_BACKOFF, _RETRY_MAX_DELAY)

    result = _mock_lookup(mc)
    _fmcsa_cache[cache_key] = result
    return result


def _parse_carrier(mc: str, c: dict) -> FMCSACarrier:
    """Map the real FMCSA API carrier payload to FMCSACarrier."""
    status_code = c.get("statusCode", "I")
    status = "ACTIVE" if status_code == "A" else status_code

    entity_type = (
        c.get("censusTypeId", {}).get("censusTypeDesc", "")
        if isinstance(c.get("censusTypeId"), dict)
        else ""
    )

    addr_parts = filter(
        None,
        [
            c.get("phyStreet", ""),
            c.get("phyCity", ""),
            c.get("phyState", ""),
            c.get("phyZipcode", ""),
        ],
    )

    return FMCSACarrier(
        mc_number=mc,
        dot_number=str(c.get("dotNumber", "")),
        legal_name=c.get("legalName", "UNKNOWN"),
        dba_name=c.get("dbaName", ""),
        status=status,
        authority_status=c.get("commonAuthorityStatus", "I"),
        entity_type=entity_type,
        safety_rating=c.get("safetyRating") or "N",
        out_of_service=c.get("allowedToOperate", "Y") != "Y",
        phone=c.get("phoneNumber", ""),
        physical_address=", ".join(addr_parts),
        bipd_insurance_on_file=int(c.get("bipdInsuranceOnFile") or 0),
        bipd_required_amount=int(c.get("bipdRequiredAmount") or 0),
        total_power_units=int(c.get("totalPowerUnits") or 0),
        total_drivers=int(c.get("totalDrivers") or 0),
        crash_total=int(c.get("crashTotal") or 0),
        driver_oos_rate=float(c.get("driverOosRate") or 0.0),
        driver_oos_rate_national_avg=float(
            c.get("driverOosRateNationalAverage") or 5.51
        ),
        mcs150_outdated=c.get("mcs150Outdated", "N") == "Y",
        oos_date=c.get("oosDate"),
    )


def _mock_lookup(mc: str) -> FMCSACarrier:
    """Realistic mock carriers for demo scenarios."""
    mocks = {
        "123456": FMCSACarrier(
            mc_number="123456",
            dot_number="1234567",
            legal_name="SWIFT HAUL LOGISTICS LLC",
            dba_name="Swift Haul",
            status="ACTIVE",
            authority_status="A",
            entity_type="CARRIER",
            safety_rating="S",
            out_of_service=False,
            phone="(555) 123-4567",
            physical_address="1234 Freight Blvd, Dallas, TX 75201",
        ),
        "789012": FMCSACarrier(
            mc_number="789012",
            dot_number="7890123",
            legal_name="HEARTLAND EXPRESS INC",
            dba_name="Heartland Express",
            status="ACTIVE",
            authority_status="A",
            entity_type="CARRIER",
            safety_rating="S",
            out_of_service=False,
            phone="(555) 789-0123",
            physical_address="567 Interstate Dr, Chicago, IL 60601",
        ),
        "456789": FMCSACarrier(
            mc_number="456789",
            dot_number="4567890",
            legal_name="COLD CHAIN CARRIERS INC",
            dba_name="Cold Chain",
            status="ACTIVE",
            authority_status="A",
            entity_type="CARRIER",
            safety_rating="S",
            out_of_service=False,
            phone="(555) 456-7890",
            physical_address="890 Reefer Rd, Atlanta, GA 30301",
        ),
        "111111": FMCSACarrier(
            mc_number="111111",
            dot_number="1111111",
            legal_name="DEFUNCT TRUCKING CO",
            dba_name="",
            status="INACTIVE",
            authority_status="I",
            entity_type="CARRIER",
            safety_rating="N",
            out_of_service=False,
        ),
        "222222": FMCSACarrier(
            mc_number="222222",
            dot_number="2222222",
            legal_name="RISKY FREIGHT LLC",
            dba_name="Risky Freight",
            status="ACTIVE",
            authority_status="A",
            entity_type="CARRIER",
            safety_rating="U",
            out_of_service=True,
            phone="(555) 222-2222",
        ),
        "333333": FMCSACarrier(
            mc_number="333333",
            dot_number="3333333",
            legal_name="NEW CARRIER PENDING LLC",
            dba_name="",
            status="ACTIVE",
            authority_status="N",
            entity_type="CARRIER",
            safety_rating="N",
            out_of_service=False,
            phone="(555) 333-3333",
        ),
    }

    return mocks.get(
        mc,
        FMCSACarrier(
            mc_number=mc,
            legal_name="UNKNOWN",
            status="NOT_FOUND",
            authority_status="N",
        ),
    )
