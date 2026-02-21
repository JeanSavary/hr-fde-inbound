"""
Test script — run after starting the server.

Usage:
  1. Start server:  uvicorn app.main:app --reload
  2. Run tests:     python test_api.py

Tests every endpoint and prints results. No pytest needed.
"""

import httpx
import sys
import json

BASE = "http://localhost:8000"
API_KEY = "dev-api-key-change-me"
HEADERS = {"X-API-Key": API_KEY}

passed = 0
failed = 0


def test(name: str, method: str, url: str, expected_status: int = 200, **kwargs):
    global passed, failed
    try:
        resp = getattr(httpx, method)(f"{BASE}{url}", headers=HEADERS, **kwargs)
        ok = resp.status_code == expected_status
        status = "✅" if ok else "❌"
        print(f"{status} {name} → {resp.status_code}")
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"   Expected {expected_status}, got {resp.status_code}")
            print(f"   Body: {resp.text[:300]}")
        return resp.json() if ok else None
    except Exception as e:
        failed += 1
        print(f"❌ {name} → ERROR: {e}")
        return None


print("=" * 60)
print("  CARRIER INBOUND SALES API — TEST SUITE")
print("=" * 60)

# ── Health ────────────────────────────────────────────────
print("\n── Health ──")
test("Health check", "get", "/health")

# ── Carrier Verification ─────────────────────────────────
print("\n── Carrier Verification ──")

data = test("Eligible carrier (123456)", "post", "/api/carriers/verify",
            json={"mc_number": "123456"})
if data:
    assert data["eligible"] is True, f"Expected eligible=True, got {data['eligible']}"
    print(f"   → {data['carrier_name']} — eligible ✓")

data = test("Inactive carrier (111111)", "post", "/api/carriers/verify",
            json={"mc_number": "111111"})
if data:
    assert data["eligible"] is False
    print(f"   → Rejected: {data['reasons']}")

data = test("OOS carrier (222222)", "post", "/api/carriers/verify",
            json={"mc_number": "222222"})
if data:
    assert data["eligible"] is False
    print(f"   → Rejected: {data['reasons']}")

data = test("Pending authority (333333)", "post", "/api/carriers/verify",
            json={"mc_number": "333333"})
if data:
    assert data["eligible"] is False
    print(f"   → Rejected: {data['reasons']}")

data = test("Unknown MC (999999)", "post", "/api/carriers/verify",
            json={"mc_number": "999999"})
if data:
    assert data["eligible"] is False
    print(f"   → Rejected: {data['reasons']}")

# ── Auth check ────────────────────────────────────────────
print("\n── Auth ──")
resp = httpx.get(f"{BASE}/api/loads/search?origin=Dallas&equipment_type=dry_van")
status = "✅" if resp.status_code == 401 else "❌"
print(f"{status} No API key → {resp.status_code}")
if resp.status_code == 401:
    passed += 1
else:
    failed += 1

resp = httpx.get(
    f"{BASE}/api/loads/search?origin=Dallas&equipment_type=dry_van",
    headers={"X-API-Key": "wrong-key"},
)
status = "✅" if resp.status_code == 401 else "❌"
print(f"{status} Wrong API key → {resp.status_code}")
if resp.status_code == 401:
    passed += 1
else:
    failed += 1

# ── Load Search ──────────────────────────────────────────
print("\n── Load Search ──")

data = test("Dallas → Houston dry_van", "get",
            "/api/loads/search?origin=Dallas&destination=Houston&equipment_type=dry_van")
if data:
    print(f"   → Found {data['total_found']} loads "
          f"(origin: {data['origin_resolved']}, dest: {data['destination_resolved']})")
    for load in data["loads"]:
        print(f"     {load['load_id']}: {load['origin']} → {load['destination']} "
              f"${load['loadboard_rate']} ({load['equipment_type']})")

data = test("DFW alias → San Antonio", "get",
            "/api/loads/search?origin=DFW&destination=San+Antonio&equipment_type=dry_van")
if data:
    print(f"   → Resolved DFW → {data['origin_resolved']}, found {data['total_found']} loads")

data = test("Fuzzy: 'dalas' → 'houton'", "get",
            "/api/loads/search?origin=dalas&destination=houton&equipment_type=dry_van")
if data:
    print(f"   → Fuzzy resolved: {data['origin_resolved']} → {data['destination_resolved']}, "
          f"found {data['total_found']}")

data = test("ATL → JAX reefer", "get",
            "/api/loads/search?origin=ATL&destination=JAX&equipment_type=reefer")
if data:
    print(f"   → Found {data['total_found']} reefer loads")

data = test("No results: NYC → LA flatbed", "get",
            "/api/loads/search?origin=NYC&destination=LA&equipment_type=flatbed")
if data:
    print(f"   → Found {data['total_found']} loads (expected 0)")

data = test("Chicago → Detroit", "get",
            "/api/loads/search?origin=Chicago&destination=Detroit&equipment_type=dry_van")
if data:
    print(f"   → Found {data['total_found']} loads")

test("Unknown origin", "get",
     "/api/loads/search?origin=Nowheresville&destination=Houston&equipment_type=dry_van",
     expected_status=404)

# ── Fort Worth radius test ────────────────────────────────
data = test("Fort Worth → OKC (within DFW radius)", "get",
            "/api/loads/search?origin=Fort+Worth&destination=Oklahoma+City&equipment_type=flatbed")
if data:
    print(f"   → Found {data['total_found']} loads (includes DFW-area origins)")

# ── Single load ──────────────────────────────────────────
print("\n── Single Load ──")
test("Get LD-1001", "get", "/api/loads/LD-1001")
test("Get non-existent load", "get", "/api/loads/LD-9999", expected_status=404)

# ── Offers ────────────────────────────────────────────────
print("\n── Offers ──")

data = test("Log initial offer", "post", "/api/offers", json={
    "load_id": "LD-1001",
    "mc_number": "123456",
    "offer_amount": 1850.00,
    "offer_type": "initial",
    "round_number": 1,
    "status": "pending",
    "call_id": "test-call-001",
})
if data:
    print(f"   → {data['offer_id']}: ${data['offer_amount']} "
          f"(floor: ${data['rate_floor']}, ceiling: ${data['rate_ceiling']})")

data = test("Log counter offer", "post", "/api/offers", json={
    "load_id": "LD-1001",
    "mc_number": "123456",
    "offer_amount": 2100.00,
    "offer_type": "counter",
    "round_number": 1,
    "status": "pending",
    "call_id": "test-call-001",
    "notes": "Carrier countered at $2100",
})
if data:
    print(f"   → {data['offer_id']}: ${data['offer_amount']} (round {data['round_number']})")

data = test("Log final offer (accepted)", "post", "/api/offers", json={
    "load_id": "LD-1001",
    "mc_number": "123456",
    "offer_amount": 1950.00,
    "offer_type": "final",
    "round_number": 2,
    "status": "accepted",
    "call_id": "test-call-001",
})
if data:
    print(f"   → {data['offer_id']}: ${data['offer_amount']} — ACCEPTED")

test("Offer for unknown load", "post", "/api/offers",
     json={"load_id": "LD-9999", "mc_number": "123456",
            "offer_amount": 1000, "offer_type": "initial"},
     expected_status=404)

# ── Call Logging ──────────────────────────────────────────
print("\n── Call Logging ──")

data = test("Log booked call", "post", "/api/calls", json={
    "call_id": "test-call-001",
    "mc_number": "123456",
    "carrier_name": "SWIFT HAUL LOGISTICS LLC",
    "lane_origin": "Dallas, TX",
    "lane_destination": "Houston, TX",
    "equipment_type": "dry_van",
    "load_id": "LD-1001",
    "initial_rate": 1850.00,
    "final_rate": 1950.00,
    "negotiation_rounds": 2,
    "carrier_phone": "(555) 123-4567",
    "outcome": "booked",
    "sentiment": "positive",
    "duration_seconds": 245,
})
if data:
    print(f"   → {data['id']}: outcome={data['outcome']}, sentiment={data['sentiment']}")

data = test("Log failed negotiation", "post", "/api/calls", json={
    "call_id": "test-call-002",
    "mc_number": "789012",
    "carrier_name": "HEARTLAND EXPRESS INC",
    "lane_origin": "Chicago, IL",
    "lane_destination": "Detroit, MI",
    "equipment_type": "dry_van",
    "load_id": "LD-1005",
    "initial_rate": 1200.00,
    "negotiation_rounds": 3,
    "outcome": "negotiation_failed",
    "sentiment": "frustrated",
    "duration_seconds": 380,
})
if data:
    print(f"   → {data['id']}: outcome={data['outcome']}, sentiment={data['sentiment']}")

data = test("Log invalid carrier call", "post", "/api/calls", json={
    "call_id": "test-call-003",
    "mc_number": "999999",
    "outcome": "invalid_carrier",
    "sentiment": "neutral",
    "duration_seconds": 60,
})
if data:
    print(f"   → {data['id']}: outcome={data['outcome']}")

# ── Dashboard ─────────────────────────────────────────────
print("\n── Dashboard ──")

data = test("Dashboard metrics", "get", "/api/dashboard/metrics")
if data:
    print(f"   Total calls    : {data['total_calls']}")
    print(f"   Booking rate   : {data['booking_rate_percent']}%")
    print(f"   Revenue        : ${data['total_revenue']}")
    print(f"   Outcomes       : {data['calls_by_outcome']}")
    print(f"   Sentiment      : {data['sentiment_distribution']}")
    print(f"   Avg rounds     : {data['avg_negotiation_rounds']}")
    print(f"   Unique carriers: {data['unique_carriers']}")

# ── Summary ───────────────────────────────────────────────
print("\n" + "=" * 60)
total = passed + failed
print(f"  RESULTS: {passed}/{total} passed", end="")
if failed:
    print(f" — {failed} FAILED ⚠️")
else:
    print(" — ALL PASSED 🎉")
print("=" * 60)

sys.exit(1 if failed else 0)
