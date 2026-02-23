"""
app/db/seed_history.py

Deterministic historical data seed for the Acme Logistics demo dashboard.
Produces ~80 realistic calls, offers, and carrier interactions spread over
the past 30 days so the dashboard never cold-starts.

On each server startup all seed data is wiped and re-inserted with
timestamps relative to the current date, so the dashboard always
shows recent activity regardless of when the server was last restarted.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

from app.db.connection import get_db

# ─── Deterministic UUID generation ────────────────────────────────────────────
_COUNTER = 0


def _uid() -> str:
    global _COUNTER
    _COUNTER += 1
    return str(uuid.UUID(int=_COUNTER * 7_919 + 0xACE1_0000_0000_0000, version=4))


def _cid() -> str:
    """Generate a HappyRobot-style call ID."""
    return "hr_" + _uid().replace("-", "")[:12]


# ─── Timestamp helper ─────────────────────────────────────────────────────────
# Set dynamically at the start of each seed run in seed_historical_data()
_BASE: datetime | None = None


def _ts(days_ago: int, hour: int = 10, minute: int = 0) -> str:
    dt = (_BASE - timedelta(days=days_ago)).replace(
        hour=hour, minute=minute, second=0, microsecond=0
    )
    return dt.isoformat()


# ─── Carriers ─────────────────────────────────────────────────────────────────
_C = [
    {"mc": "MC-847291", "name": "Sunrise Transport LLC",     "phone": "+15125550192"},
    {"mc": "MC-392847", "name": "Blue Ridge Freight Inc",    "phone": "+14045558234"},
    {"mc": "MC-751034", "name": "Lone Star Carriers",        "phone": "+12145557891"},
    {"mc": "MC-628405", "name": "Pacific Haul Co",           "phone": "+13235556734"},
    {"mc": "MC-193847", "name": "Great Plains Trucking",     "phone": "+19135554521"},
    {"mc": "MC-847523", "name": "Appalachian Freight LLC",   "phone": "+19015553218"},
    {"mc": "MC-302847", "name": "Desert Run Transport",      "phone": "+16025552109"},
    {"mc": "MC-574839", "name": "Midwest Express Inc",       "phone": "+13125559876"},
    {"mc": "MC-918273", "name": "Southeast Carriers LLC",    "phone": "+17705551234"},
    {"mc": "MC-463728", "name": "Rocky Mountain Freight",    "phone": "+17205558765"},
    {"mc": "MC-829374", "name": "Gulf Coast Transport",      "phone": "+17135556543"},
    {"mc": "MC-192847", "name": "Northern Star Logistics",   "phone": "+16125554321"},
    {"mc": "MC-748293", "name": "Coastal Freight Solutions", "phone": "+18585557890"},
    {"mc": "MC-374829", "name": "Heartland Carriers Inc",    "phone": "+15155553456"},
    {"mc": "MC-928374", "name": "TruckRight LLC",            "phone": "+14692221987"},
]

_INVALID = [
    {"mc": "MC-000011", "name": None, "phone": "+19991110001"},
    {"mc": "MC-000022", "name": None, "phone": "+19991110002"},
    {"mc": "MC-000033", "name": None, "phone": "+19991110003"},
    {"mc": "MC-000044", "name": None, "phone": "+19991110004"},
    {"mc": "MC-000055", "name": None, "phone": "+19991110005"},
]

# ─── Transcripts ──────────────────────────────────────────────────────────────

T_BOOKED_QUICK = (
    "Agent: Acme Logistics, this is John. How can I help you today?\n"
    "Carrier: Hey, calling about the load you've got posted. Is it still open?\n"
    "Agent: Yep, still available. Can I get your MC number real quick?\n"
    "Carrier: Sure — {mc}.\n"
    "Agent: Perfect, you're verified. Alright, {origin} to {dest} — {equip}, "
    "{miles} miles. I've got it at ${loadboard:,.0f} all-in. Does that work for you?\n"
    "Carrier: Yeah, ${loadboard:,.0f} works. We're repositioning that direction anyway.\n"
    "Agent: Great. I'll get the rate confirmation over to you. Anything else you need?\n"
    "Carrier: No, that covers it. Send it over.\n"
    "Agent: Done. Thanks for the call."
)

T_BOOKED_2R = (
    "Agent: Acme Logistics, John here.\n"
    "Carrier: Hey John, this is {carrier} calling. I'm looking at your {origin} to {dest} {equip} load.\n"
    "Agent: Hey, good timing — that's still open. MC number for me?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified, you're good. {origin} to {dest}, {miles} miles, {equip}. "
    "I've got that posted at ${loadboard:,.0f} all-in. If I can hold ${loadboard:,.0f}, can you run it?\n"
    "Carrier: I need a bit more than that. Deadhead's not cheap and the destination "
    "isn't the greatest reload market. I'm thinking ${carrier_ask:,.0f}.\n"
    "Agent: Yeah I hear you on the deadhead — that's a real cost. I can come up some. "
    "How about ${mid:,.0f}?\n"
    "Carrier: Can you do ${agreed:,.0f}?\n"
    "Agent: Let me see... yeah, ${agreed:,.0f} I can make work. That's the best I can do on this one.\n"
    "Carrier: Alright, ${agreed:,.0f} works. Let's do it.\n"
    "Agent: Perfect. So we're at ${agreed:,.0f} all-in. "
    "I'll get the rate confirmation over now. Appreciate the call."
)

T_BOOKED_3R = (
    "Agent: Acme Logistics, this is John.\n"
    "Carrier: Hey, this is {carrier}. Calling about the {origin} to {dest} {equip}.\n"
    "Agent: Yeah, still open. MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified. {origin} to {dest}, {equip}, {miles} miles. "
    "Posted at ${loadboard:,.0f}. Can you cover it at ${loadboard:,.0f}?\n"
    "Carrier: No, I need more. Fuel is up and that lane's tough right now. I need ${carrier_ask:,.0f}.\n"
    "Agent: Yeah I hear you on fuel. That's a pretty big gap though. "
    "I can come to ${r2:,.0f} — that's a meaningful move from where I started.\n"
    "Carrier: Still need at least ${r2_carrier:,.0f}.\n"
    "Agent: I understand, but I'm getting tight on this one. "
    "Best I can do is ${agreed:,.0f} — that's truly my ceiling here.\n"
    "Carrier: Alright. ${agreed:,.0f} and we've got a deal.\n"
    "Agent: Done. ${agreed:,.0f} all-in. Confirmation coming your way. Thanks for working with me on it."
)

T_BOOKED_REEFER = (
    "Agent: Acme Logistics, John speaking.\n"
    "Carrier: Hey John, {carrier} here. You've got a reefer move posted — {origin} to {dest}?\n"
    "Agent: That's right, still available. MC number for verification?\n"
    "Carrier: {mc}.\n"
    "Agent: Perfect, you're good. {origin} to {dest}, {miles} miles, reefer, temp-controlled. "
    "Posted at ${loadboard:,.0f} all-in — that's everything including the temp requirement. "
    "Does ${loadboard:,.0f} work?\n"
    "Carrier: We do a lot of produce runs but ${carrier_ask:,.0f} is where I need to be. "
    "Long haul like this, reefer fuel adds up fast.\n"
    "Agent: Totally valid — reefer fuel's real on a {miles}-mile run. I can come up to ${mid:,.0f}. "
    "That's a solid move.\n"
    "Carrier: If you can do ${agreed:,.0f} we're done right now.\n"
    "Agent: ${agreed:,.0f} works. Let's get this booked. "
    "I'll send confirmation — temp hold at specified setting, pre-cool required. "
    "Anything else you need?\n"
    "Carrier: No, that covers it. Thanks John.\n"
    "Agent: Thank you. Have a good one."
)

T_FAILED_PRICE = (
    "Agent: Acme Logistics, this is John.\n"
    "Carrier: Hey, calling about the {origin} to {dest} {equip}.\n"
    "Agent: Still open. MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified. {origin} to {dest}, {equip}, {miles} miles. "
    "I've got that at ${loadboard:,.0f}. Can you do ${loadboard:,.0f} all-in?\n"
    "Carrier: I need ${carrier_ask:,.0f}. Fuel is up, that's a tough lane for reloads.\n"
    "Agent: Yeah fuel's been rough. I can come up a little — ${r2:,.0f}. That's real movement.\n"
    "Carrier: Still need ${r2_carrier:,.0f} minimum. My costs are high right now.\n"
    "Agent: I hear you but I'm getting tight. ${r3:,.0f} is truly the best I can do. Final answer.\n"
    "Carrier: ${r3:,.0f} doesn't work for me. I'll pass.\n"
    "Agent: No worries — if the rate opens up I'll reach back out. "
    "What lanes and rates are you targeting today?\n"
    "Carrier: {equip} freight, {origin} area, need at least ${carrier_ask:,.0f}.\n"
    "Agent: Got it, I'll keep that in mind. Thanks for calling."
)

T_FAILED_EQUIP = (
    "Agent: Acme Logistics, John here.\n"
    "Carrier: Hey, I've got a {caller_equip} available. Saw your {origin} to {dest} posted.\n"
    "Agent: Good timing — still open. MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified, you're good. The {origin} to {dest} is a {equip} load though. "
    "You mentioned {caller_equip}?\n"
    "Carrier: Yeah, I've got a {caller_equip}. Figured it might work for your load.\n"
    "Agent: I'd love to make it work, but the commodity and securement on this one requires {equip}. "
    "I can't swap equipment without shipper sign-off and I'd rather not risk the load.\n"
    "Carrier: Makes sense. You got anything else going my way for {caller_equip}?\n"
    "Agent: Let me check... nothing that's a clean match right now on my end. "
    "Give me a call tomorrow — we get new posts daily and I'll keep an eye out.\n"
    "Carrier: Alright, I'll try back. Thanks.\n"
    "Agent: Appreciate the call. Talk soon."
)

T_NO_LOADS = (
    "Agent: Acme Logistics, this is John.\n"
    "Carrier: Hey, I've got a {equip} running empty out of {origin}. "
    "Looking for something heading {direction}.\n"
    "Agent: Got it. MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified. Let me search... {equip}, {origin} area, heading {direction}. "
    "Pickup availability?\n"
    "Carrier: Available now through tomorrow.\n"
    "Agent: Let me check... I'm not seeing a clean match for {equip} out of {origin} heading {direction} "
    "right now. Could shift later — we get new loads posted throughout the day.\n"
    "Carrier: Nothing at all?\n"
    "Agent: Not right now, sorry. I can take your info and reach back out if something opens up. "
    "This number good?\n"
    "Carrier: Yeah, call me back on this line.\n"
    "Agent: Got it — noted. {equip}, {origin}, heading {direction}. "
    "We'll be in touch if something comes through."
)

T_INVALID = (
    "Agent: Acme Logistics, John speaking.\n"
    "Carrier: Hey, I'm calling about a load you have posted.\n"
    "Agent: Sure. Can I get your MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: One second to verify... I'm seeing an issue with the authority on file for that MC. "
    "It's showing as {reason} — I can't book loads until that's resolved.\n"
    "Carrier: Really? We're definitely operating.\n"
    "Agent: I hear you — worth checking directly with FMCSA at fmcsa.dot.gov. "
    "They'll have the current status. Once it's sorted, reach back out and we'd love to work together.\n"
    "Carrier: Alright.\n"
    "Agent: Thanks for calling. Sorry I couldn't help today."
)

T_THINKING = (
    "Agent: Acme Logistics, this is John.\n"
    "Carrier: Hey, this is {carrier}. Saw your {origin} to {dest} {equip} posted. Still open?\n"
    "Agent: Yep, still available. MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified. {origin} to {dest}, {equip}, {miles} miles. "
    "I've got it at ${loadboard:,.0f} all-in. Does ${loadboard:,.0f} work?\n"
    "Carrier: My driver's coming from a bit of a distance, so there's deadhead. "
    "Can you do ${carrier_ask:,.0f}?\n"
    "Agent: Yeah deadhead's a real cost. I can come up to ${mid:,.0f}.\n"
    "Carrier: Let me check with my dispatcher. Can I call you back in 20 minutes?\n"
    "Agent: Absolutely — load's still open. Just call this number back.\n"
    "Carrier: Will do. Give me 20 minutes.\n"
    "Agent: Sounds good. Talk soon."
)

T_TRANSFERRED = (
    "Agent: Acme Logistics, John here.\n"
    "Carrier: Hey, I've got a question about a load — the weight is {weight:,} lbs. "
    "I want to make sure we're good on permits.\n"
    "Agent: Got it. MC number?\n"
    "Carrier: {mc}.\n"
    "Agent: Verified. At {weight:,} lbs we're in territory where permits depend on "
    "the route and your axle config. That's something our ops team handles directly — "
    "I don't want to give you wrong info on permitting.\n"
    "Carrier: Yeah I just want to make sure we're covered before I commit.\n"
    "Agent: Totally understand. I'm going to transfer you to our ops desk right now. "
    "They'll walk through the permit requirements with you.\n"
    "Carrier: Okay, thanks.\n"
    "Agent: One moment — transferring you now."
)

T_DROPPED = (
    "Agent: Acme Logistics, this is John. How can I—\n"
    "Carrier: Hey yeah, I'm calling about—\n"
    "[Call disconnected]"
)

# ─── Booked load specs ────────────────────────────────────────────────────────
# (load_id, origin, dest, equip, miles, loadboard, carrier_ask, agreed,
#  carrier_idx, days_ago, hour, minute, duration, rounds, sentiment,
#  transcript_key, summary, key_points)

_BOOKED = [
    # ── NORMAL MARGIN (~5.6%) — 2-round ─────────────────────────────
    # loadboard_rate=2150, floor=1935, ceil=2365, agreed=2030
    (
        "LD-1001", "Dallas, TX", "Chicago, IL", "dry_van", 920,
        1935, 2100, 2030, 0, 30, 9, 12, 258, 2, "positive", "2r",
        "Carrier called on Dallas to Chicago dry van. Negotiated from $2,100 ask down to "
        "$2,030 in 2 rounds. Carrier cited deadhead from Oklahoma City.",
        ["Carrier had ~150 mi deadhead from Oklahoma City",
         "Rate negotiated from $2,100 ask to $2,030 in 2 rounds",
         "Agreed $2,030 all-in — deal closed"],
    ),
    # ── NORMAL MARGIN (~4.9%) — 2-round reefer ──────────────────────
    # loadboard_rate=1850, floor=1665, ceil=2035, agreed=1760
    (
        "LD-1002", "Atlanta, GA", "Miami, FL", "reefer", 662,
        1665, 1830, 1760, 8, 28, 11, 7, 231, 2, "positive", "reefer",
        "Southeast Carriers called on Atlanta to Miami reefer. Carrier cited Miami reload "
        "difficulty and reefer fuel costs. 2-round negotiation, settled $1,760.",
        ["Carrier raised Miami dead-end concern and reefer fuel",
         "Quick 2-round negotiation — carrier familiar with lane",
         "Agreed $1,760 all-in, temp 34°F confirmed"],
    ),
    # ── TIGHT MARGIN (~2.0%) — 3-round ──────────────────────────────
    # loadboard_rate=980, floor=882, ceil=1078, agreed=960
    (
        "LD-1003", "Los Angeles, CA", "Phoenix, AZ", "flatbed", 373,
        885, 1020, 960, 3, 27, 14, 23, 312, 3, "neutral", "3r",
        "Pacific Haul called on LA to Phoenix flatbed — steel coils. Three-round "
        "negotiation. Carrier flagged weight at 44,000 lbs and tarping costs. Agreed $960.",
        ["Carrier flagged heavy load at 44,000 lbs near legal limit",
         "Three rounds of negotiation — carrier pushed hard on tarping premium",
         "Agreed $960 all-in — tight margin after hard negotiation"],
    ),
    # ── TIGHT MARGIN (~2.8%) — 3-round ──────────────────────────────
    # loadboard_rate=1420, floor=1278, ceil=1562, agreed=1380
    (
        "LD-1004", "Houston, TX", "Memphis, TN", "dry_van", 586,
        1280, 1440, 1380, 10, 25, 8, 44, 347, 3, "neutral", "3r",
        "Gulf Coast Transport called on Houston to Memphis dry van. Three rounds — "
        "carrier pushed on fuel costs and Memphis dead-end market. Agreed $1,380.",
        ["Carrier cited fuel costs and Memphis as tough reload market",
         "Three rounds before final agreement",
         "Agreed $1,380 all-in — tight margin after extended negotiation"],
    ),
    # ── NORMAL MARGIN (~5.0%) — 2-round reefer ──────────────────────
    # loadboard_rate=3200, floor=2880, ceil=3520, agreed=3040
    (
        "LD-1006", "Salinas, CA", "Denver, CO", "reefer", 1140,
        2880, 3150, 3040, 4, 24, 7, 5, 389, 2, "positive", "reefer",
        "Great Plains Trucking called on Salinas to Denver reefer — 1,140-mile produce haul. "
        "Carrier had strong case for long-haul reefer fuel. Settled $3,040 in 2 rounds.",
        ["Long-haul 1,140 miles — carrier had valid reefer fuel argument",
         "Pre-cool to 33°F requirement acknowledged",
         "Agreed $3,040 all-in — 2-round deal"],
    ),
    # ── NORMAL MARGIN (~4.7%) — 2-round reefer ──────────────────────
    # loadboard_rate=1380, floor=1242, ceil=1518, agreed=1315
    (
        "LD-1012", "Kansas City, MO", "Minneapolis, MN", "reefer", 443,
        1245, 1370, 1315, 8, 22, 10, 18, 275, 2, "positive", "reefer",
        "Southeast Carriers called on Kansas City to Minneapolis reefer — frozen meat. "
        "Carrier cited temp certification costs. 2-round deal at $1,315.",
        ["Sealed trailer required — frozen meat at 0°F",
         "Carrier had temp certification on file",
         "Agreed $1,315 all-in in 2 rounds"],
    ),
    # ── GREAT MARGIN (~9.0%) — 1-round quick ────────────────────────
    # loadboard_rate=780, floor=702, ceil=858, agreed=710
    (
        "LD-1015", "Philadelphia, PA", "Richmond, VA", "reefer", 290,
        710, 710, 710, 11, 20, 13, 33, 198, 1, "positive", "quick",
        "Northern Star Logistics called on Philadelphia to Richmond dairy reefer. "
        "Carrier positioned nearby with available reefer. Quick 1-round deal at $710.",
        ["Carrier had empty reefer nearby — strong positioning",
         "Short haul 290 miles, dairy at 36°F",
         "Agreed $710 all-in — quick 1-round acceptance"],
    ),
    # ── GREAT MARGIN (~8.7%) — 1-round quick ────────────────────────
    # loadboard_rate=750, floor=675, ceil=825, agreed=685
    (
        "LD-1018", "Louisville, KY", "St. Louis, MO", "dry_van", 264,
        685, 685, 685, 7, 18, 9, 51, 187, 1, "positive", "quick",
        "Midwest Express called on Louisville to St. Louis dry van. Short haul, "
        "floor-loaded beverages. Carrier accepted immediately at $685.",
        ["Floor-loaded beverages — no pallets, noted by carrier",
         "Carrier was positioning toward St. Louis anyway",
         "Agreed $685 all-in — 1-round quick deal"],
    ),
    # ── NORMAL MARGIN (~5.1%) — 2-round ─────────────────────────────
    # loadboard_rate=1280, floor=1152, ceil=1408, agreed=1215
    (
        "LD-1020", "San Antonio, TX", "New Orleans, LA", "dry_van", 542,
        1155, 1260, 1215, 2, 16, 11, 9, 243, 2, "positive", "2r",
        "Lone Star Carriers called on San Antonio to New Orleans dry van. "
        "Carrier had favorable positioning from SA. 2-round deal at $1,215.",
        ["Carrier positioned in San Antonio — minimal deadhead",
         "E-commerce fulfillment, dock lock required confirmed",
         "Agreed $1,215 all-in in 2 rounds"],
    ),
    # ── GREAT MARGIN (~9.4%) — 1-round quick ────────────────────────
    # loadboard_rate=850, floor=765, ceil=935, agreed=770
    (
        "LD-1025", "El Paso, TX", "Tucson, AZ", "flatbed", 263,
        770, 770, 770, 13, 14, 15, 22, 145, 1, "positive", "quick",
        "Heartland Carriers called on El Paso to Tucson flatbed — solar equipment. "
        "Quick 1-round deal, carrier repositioning that direction. $770 all-in.",
        ["Carrier was repositioning El Paso to Tucson anyway",
         "Solar panels on pallets — edge protectors and tarps confirmed",
         "1-round quick deal at $770 all-in"],
    ),
    # ── NORMAL MARGIN (~4.7%) — 2-round ─────────────────────────────
    # loadboard_rate=1180, floor=1062, ceil=1298, agreed=1125
    (
        "LD-1030", "Harrisburg, PA", "Charlotte, NC", "dry_van", 480,
        1065, 1170, 1125, 5, 12, 8, 37, 267, 2, "positive", "2r",
        "Appalachian Freight called on Harrisburg to Charlotte dry van — furniture load. "
        "Carrier familiar with lane. Clean 2-round deal at $1,125.",
        ["Pad wrap / blanket wrap requirement confirmed",
         "Carrier runs this lane regularly",
         "Agreed $1,125 all-in — 2-round deal"],
    ),
    # ── NEGATIVE MARGIN (~-3.6%) — 3-round ──────────────────────────
    # loadboard_rate=1950, floor=1755, ceil=2145, agreed=2020
    (
        "LD-1031", "Atlanta, GA", "Dallas, TX", "dry_van", 781,
        1755, 2200, 2020, 1, 10, 10, 14, 334, 3, "neutral", "3r",
        "Blue Ridge Freight called on Atlanta to Dallas dry van — home improvement products. "
        "Three rounds of hard negotiation. Carrier pushed to $2,200, settled at $2,020. "
        "Negative margin accepted to avoid load expiration.",
        ["Carrier pushed hard citing fuel and long haul — opened at $2,200",
         "Three rounds required — broker stretched beyond loadboard rate",
         "Agreed $2,020 all-in — load was time-sensitive, liftgate at delivery confirmed"],
    ),
    # ── NORMAL MARGIN (~4.5%) — 2-round ─────────────────────────────
    # loadboard_rate=1550, floor=1395, ceil=1705, agreed=1480
    (
        "LD-1037", "Houston, TX", "Memphis, TN", "dry_van", 586,
        1395, 1540, 1480, 4, 8, 7, 48, 289, 2, "positive", "2r",
        "Great Plains Trucking called on Houston to Memphis dry van — industrial equipment. "
        "Carrier positioned in Houston. 2-round deal at $1,480.",
        ["High-value cargo — carrier confirmed strapping capability",
         "Carrier had truck available in Houston yard",
         "Agreed $1,480 all-in in 2 rounds"],
    ),
    # ── NEGATIVE MARGIN (~-3.6%) — 3-round ──────────────────────────
    # loadboard_rate=1100, floor=990, ceil=1210, agreed=1140
    (
        "LD-1043", "Atlanta, GA", "Jacksonville, FL", "step_deck", 346,
        990, 1250, 1140, 12, 5, 14, 2, 251, 3, "neutral", "3r",
        "Coastal Freight Solutions called on Atlanta to Jacksonville step deck — "
        "transformer unit, 11ft over-height. Carrier had specialized equipment and "
        "pushed hard on rate. Agreed $1,140 — negative margin on limited carrier pool.",
        ["Over-height 11ft transformer — wide load permit verified",
         "Carrier had step deck with correct securement — limited carrier pool",
         "Agreed $1,140 all-in — specialized equipment justified premium"],
    ),
    # ── GREAT MARGIN (~9.1%) — 1-round quick ────────────────────────
    # loadboard_rate=550, floor=495, ceil=605, agreed=500
    (
        "LD-1047", "Dallas, TX", "Houston, TX", "power_only", 239,
        500, 500, 500, 14, 3, 9, 27, 132, 1, "positive", "quick",
        "TruckRight LLC called on Dallas to Houston power only. Hook-and-go drop trailer. "
        "Carrier repositioning south. Quick 1-round deal at $500.",
        ["Drop-and-hook trailer — carrier confirmed 53ft capacity",
         "Carrier was repositioning Dallas to Houston anyway",
         "Quick 1-round deal at $500 all-in"],
    ),
]

# ─── Failed negotiation specs ─────────────────────────────────────────────────
# (carrier_idx, load_id, origin, dest, equip, miles, loadboard,
#  carrier_ask, agent_r2, agent_r3, days_ago, hour, minute, duration,
#  rounds, sentiment)

_FAILED = [
    (1,  "LD-1005", "Chicago, IL",      "Detroit, MI",      "dry_van",   282,  720,  1100,  800,  820, 29, 14, 11, 298, 3, "frustrated"),
    (6,  "LD-1007", "Charlotte, NC",    "Nashville, TN",    "flatbed",   410, 1050, 1500, 1150, 1160, 27, 11, 33, 312, 3, "frustrated"),
    (9,  "LD-1008", "Newark, NJ",       "Boston, MA",       "reefer",    215,  680,  950,  750,  760, 26,  9, 22, 287, 3, "frustrated"),
    (2,  "LD-1009", "Indianapolis, IN", "Columbus, OH",     "dry_van",   175,  520,  800,  575,    0, 25, 16, 44, 223, 2, "neutral"),
    (11, "LD-1010", "Laredo, TX",       "San Antonio, TX",  "dry_van",   155,  450,  700,  490,    0, 24, 10, 17, 198, 2, "neutral"),
    (0,  "LD-1011", "Seattle, WA",      "Portland, OR",     "flatbed",   174,  580,  900,  640,  648, 23, 13, 5,  276, 3, "frustrated"),
    (7,  "LD-1013", "Jacksonville, FL", "Savannah, GA",     "dry_van",   139,  420,  700,  460,    0, 22,  8, 55, 201, 2, "neutral"),
    (4,  "LD-1014", "Denver, CO",       "Albuquerque, NM",  "dry_van",   449, 1100, 1500, 1210, 1215, 21, 11, 28, 318, 3, "frustrated"),
    (13, "LD-1016", "Fort Worth, TX",   "Oklahoma City, OK","flatbed",   200,  620, 1000,  690,  695, 20, 15, 41, 299, 3, "frustrated"),
    (5,  "LD-1017", "Sacramento, CA",   "Reno, NV",         "dry_van",   135,  480,  700,  530,    0, 19, 10,  9, 187, 2, "neutral"),
    (3,  "LD-1019", "Milwaukee, WI",    "Des Moines, IA",   "reefer",    350,  920, 1300, 1020, 1030, 18,  9, 33, 321, 3, "frustrated"),
    (8,  "LD-1022", "Fresno, CA",       "Las Vegas, NV",    "reefer",    270,  950, 1350, 1050, 1060, 17, 11, 18, 334, 3, "frustrated"),
    (12, "LD-1023", "Nashville, TN",    "Birmingham, AL",   "dry_van",   191,  520,  800,  575,    0, 16,  8, 47, 198, 2, "neutral"),
    (1,  "LD-1024", "Columbus, OH",     "Buffalo, NY",      "dry_van",   340,  820, 1200,  910,  915, 15, 13, 22, 289, 3, "frustrated"),
    (6,  "LD-1026", "Bakersfield, CA",  "Salt Lake City, UT","reefer",   725, 2100, 2700, 2310, 2320, 13,  9, 14, 367, 3, "frustrated"),
    (9,  "LD-1027", "Omaha, NE",        "Wichita, KS",      "reefer",    260,  680, 1000,  750,    0, 12, 11, 38, 243, 2, "neutral"),
    (2,  "LD-1028", "Tampa, FL",        "Orlando, FL",      "dry_van",    84,  340,  600,  380,  385, 11, 10, 52, 221, 3, "frustrated"),
    (11, "LD-1029", "Little Rock, AR",  "Dallas, TX",       "dry_van",   318,  820, 1100,  910,  915, 10, 14, 7,  287, 3, "frustrated"),
    (0,  "LD-1032", "Atlanta, GA",      "Houston, TX",      "dry_van",   790, 1800, 2400, 1980, 1990,  9,  9, 33, 354, 3, "frustrated"),
    (7,  "LD-1033", "Atlanta, GA",      "Charlotte, NC",    "flatbed",   244,  680, 1000,  750,    0,  8, 11, 18, 234, 2, "neutral"),
    (4,  "LD-1034", "Atlanta, GA",      "Nashville, TN",    "reefer",    249,  920, 1300, 1020, 1030,  7, 13, 44, 312, 3, "frustrated"),
    (13, "LD-1035", "Memphis, TN",      "Dallas, TX",       "dry_van",   452, 1350, 1800, 1490, 1495,  6, 10, 29, 298, 3, "frustrated"),
    (5,  "LD-1036", "New Orleans, LA",  "Houston, TX",      "dry_van",   348,  850, 1200,  940,    0,  5, 14, 13, 223, 2, "neutral"),
    (3,  "LD-1038", "Fort Worth, TX",   "San Antonio, TX",  "dry_van",   264,  580,  900,  640,    0,  4,  9, 47, 198, 2, "neutral"),
    (10, "LD-1039", "Dallas, TX",       "Fort Worth, TX",   "dry_van",    32,  250,  450,  275,  278,  1, 11, 22, 198, 3, "frustrated"),
]

# ─── No-loads specs ───────────────────────────────────────────────────────────
# (carrier_idx, origin, equip, direction, days_ago, hour, minute, duration)

_NO_LOADS = [
    (9,  "Seattle, WA",        "reefer",     "south to California", 29, 10, 22, 95),
    (6,  "Minneapolis, MN",    "dry_van",    "southeast",           28, 13, 41, 110),
    (12, "Miami, FL",          "flatbed",    "north",               27,  9, 17, 85),
    (3,  "Portland, OR",       "reefer",     "south",               26, 15, 33, 120),
    (0,  "Detroit, MI",        "dry_van",    "south to Tennessee",  24,  8, 11, 90),
    (7,  "Reno, NV",           "step_deck",  "east",                23, 11, 52, 75),
    (10, "Albuquerque, NM",    "reefer",     "west to California",  22, 14, 7,  105),
    (4,  "Pittsburgh, PA",     "power_only", "midwest",             21,  9, 44, 95),
    (11, "Salt Lake City, UT", "dry_van",    "east",                20, 10, 28, 85),
    (1,  "Omaha, NE",          "flatbed",    "south to Texas",      17, 13, 15, 95),
    (8,  "Indianapolis, IN",   "reefer",     "northeast",           16,  8, 37, 110),
    (13, "Richmond, VA",       "dry_van",    "southeast",           15, 11, 22, 90),
    (2,  "Wichita, KS",        "dry_van",    "south",               14, 15, 48, 85),
    (5,  "Buffalo, NY",        "reefer",     "midwest",             11,  9, 19, 105),
    (14, "El Paso, TX",        "flatbed",    "east to Texas",       10, 10, 33, 90),
    (6,  "Birmingham, AL",     "dry_van",    "north to midwest",     9, 14, 7,  95),
    (9,  "Sacramento, CA",     "reefer",     "east to Nevada",       7,  8, 44, 110),
    (3,  "Milwaukee, WI",      "step_deck",  "south",                6, 11, 22, 85),
    (0,  "Louisville, KY",     "dry_van",    "southeast",            4,  9, 15, 90),
    (12, "Oklahoma City, OK",  "flatbed",    "west",                 0,  7, 38, 80),
]

# ─── Invalid carrier specs ────────────────────────────────────────────────────
# (invalid_idx, reason, days_ago, hour, minute, duration)

_INVALID_CALLS = [
    (0, "out-of-service",       29, 11, 22, 45),
    (1, "inactive authority",   27,  9, 41, 52),
    (2, "insufficient insurance", 25, 14, 7, 38),
    (0, "out-of-service",       23, 10, 33, 44),
    (3, "inactive authority",   21,  8, 18, 56),
    (1, "insufficient insurance", 18, 11, 47, 41),
    (4, "inactive authority",   15, 13, 22, 48),
    (2, "out-of-service",       12,  9, 15, 43),
    (3, "inactive authority",    8, 15, 38, 51),
    (0, "out-of-service",        0,  9, 7,  46),
]

# ─── Carrier-thinking specs ───────────────────────────────────────────────────
# (carrier_idx, load_id, origin, dest, equip, miles, loadboard, carrier_ask,
#  days_ago, hour, minute, duration)

_THINKING = [
    (0,  "LD-1040", "Dallas, TX",    "Austin, TX",      "dry_van",   195, 420, 550,  9,  9, 22, 185),
    (7,  "LD-1041", "Dallas, TX",    "Houston, TX",     "flatbed",   239, 650, 850,  7, 11, 44, 195),
    (2,  "LD-1044", "Chicago, IL",   "Indianapolis, IN","step_deck", 184, 720, 900,  5, 14, 17, 210),
    (9,  "LD-1045", "Phoenix, AZ",   "Los Angeles, CA", "step_deck", 373, 850,1050,  3,  9, 33, 180),
    (5,  "LD-1042", "Houston, TX",   "Dallas, TX",      "step_deck", 239, 980,1200,  2, 11,  7, 190),
    (11, "LD-1046", "Dallas, TX",    "Memphis, TN",     "step_deck", 452,1200,1500,  0,  8, 48, 175),
]

# ─── Transferred-to-ops specs ─────────────────────────────────────────────────
# (carrier_idx, load_id, weight, days_ago, hour, minute, duration)

_TRANSFERRED = [
    (4,  "LD-1021", 47000, 17, 10, 33, 125),
    (7,  "LD-1033", 45000, 12, 14, 18, 135),
    (11, "LD-1046", 35000,  6,  9, 44, 145),
    (2,  "LD-1016", 43000,  2, 11, 22, 130),
]

# ─── Dropped call specs ───────────────────────────────────────────────────────
# (carrier_idx, load_id, days_ago, hour, minute, duration)

_DROPPED = [
    (3, "LD-1048", 20,  8,  7, 28),
    (8, "LD-1050", 11, 13, 44, 22),
]

# ─── Offer helpers ────────────────────────────────────────────────────────────


def _offer(call_id, load_id, mc, amount, otype, rnum, status, loadboard, ts_base, min_offset):
    diff = round(amount - loadboard, 2)
    pct = round((diff / loadboard) * 100, 2) if loadboard else 0.0
    return {
        "offer_id": _uid(),
        "call_id": call_id,
        "load_id": load_id,
        "mc_number": mc,
        "offer_amount": amount,
        "offer_type": otype,
        "round_number": rnum,
        "status": status,
        "notes": "",
        "created_at": (datetime.fromisoformat(ts_base) + timedelta(minutes=min_offset)).isoformat(),
        "original_rate": loadboard,
        "rate_difference": diff,
        "rate_difference_pct": pct,
        "original_pickup_datetime": None,
        "agreed_pickup_datetime": None,
        "pickup_changed": 0,
    }


def _build_offers_booked(call_id, load_id, mc, loadboard, carrier_ask, agreed, rounds, ts):
    offers = []
    mid = round((carrier_ask + loadboard) / 2 / 5) * 5  # round to nearest $5

    # Round 1: carrier's initial ask
    offers.append(_offer(call_id, load_id, mc, carrier_ask, "initial", 1, "rejected", loadboard, ts, 2))

    if rounds == 1:
        offers.append(_offer(call_id, load_id, mc, agreed, "final", 2, "accepted", loadboard, ts, 5))
    elif rounds == 2:
        offers.append(_offer(call_id, load_id, mc, mid, "counter", 2, "rejected", loadboard, ts, 4))
        offers.append(_offer(call_id, load_id, mc, agreed, "final", 3, "accepted", loadboard, ts, 7))
    else:  # 3 rounds
        offers.append(_offer(call_id, load_id, mc, mid, "counter", 2, "rejected", loadboard, ts, 4))
        offers.append(_offer(call_id, load_id, mc, agreed, "final", 3, "accepted", loadboard, ts, 8))

    return offers


def _build_offers_failed(call_id, load_id, mc, loadboard, carrier_ask, agent_r2, agent_r3, rounds, ts):
    offers = []
    offers.append(_offer(call_id, load_id, mc, carrier_ask, "initial", 1, "rejected", loadboard, ts, 2))

    if rounds == 2:
        offers.append(_offer(call_id, load_id, mc, agent_r2, "counter", 2, "rejected", loadboard, ts, 5))
    else:
        offers.append(_offer(call_id, load_id, mc, agent_r2, "counter", 2, "rejected", loadboard, ts, 4))
        offers.append(_offer(call_id, load_id, mc, agent_r3, "final", 3, "rejected", loadboard, ts, 8))

    return offers


def _build_offers_thinking(call_id, load_id, mc, loadboard, carrier_ask, ts):
    mid = round((carrier_ask + loadboard) / 2 / 5) * 5
    return [
        _offer(call_id, load_id, mc, carrier_ask, "initial", 1, "pending", loadboard, ts, 2),
        _offer(call_id, load_id, mc, mid, "counter", 2, "pending", loadboard, ts, 5),
    ]


# ─── Interaction helper ────────────────────────────────────────────────────────


def _interaction(mc, name, call_id, load_id, outcome, duration, created_at):
    return {
        "id": _uid(),
        "mc_number": mc,
        "carrier_name": name,
        "call_id": call_id,
        "call_length_seconds": duration,
        "outcome": outcome,
        "load_id": load_id,
        "notes": "",
        "created_at": created_at,
    }


# ─── Main data builder ────────────────────────────────────────────────────────


def _build_data():
    calls = []
    offers = []
    interactions = []

    # ── BOOKED calls ─────────────────────────────────────────────────────────
    tx_map = {
        "quick":  T_BOOKED_QUICK,
        "2r":     T_BOOKED_2R,
        "3r":     T_BOOKED_3R,
        "reefer": T_BOOKED_REEFER,
    }

    for row in _BOOKED:
        (
            load_id, origin, dest, equip, miles,
            loadboard, carrier_ask, agreed,
            cidx, days_ago, hour, minute, duration,
            rounds, sentiment, tx_key,
            summary, key_points,
        ) = row

        carrier = _C[cidx]
        mc = carrier["mc"]
        name = carrier["name"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)
        mid = round((carrier_ask + loadboard) / 2 / 5) * 5

        tx_tpl = tx_map[tx_key]
        try:
            transcript = tx_tpl.format(
                mc=mc, carrier=name, origin=origin, dest=dest,
                equip=equip.replace("_", " "), miles=miles,
                loadboard=loadboard, carrier_ask=carrier_ask,
                agreed=agreed, mid=mid,
                r2=mid, r2_carrier=round(mid * 1.05 / 5) * 5,
            )
        except KeyError:
            transcript = tx_tpl

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": name,
            "lane_origin": origin, "lane_destination": dest,
            "equipment_type": equip, "load_id": load_id,
            "initial_rate": float(carrier_ask), "final_rate": float(agreed),
            "negotiation_rounds": rounds,
            "carrier_phone": carrier["phone"],
            "special_requests": None, "outcome": "booked",
            "sentiment": sentiment, "duration_seconds": duration,
            "transcript": transcript, "summary": summary,
            "key_points": json.dumps(key_points), "created_at": ts,
        })

        offers.extend(_build_offers_booked(call_id, load_id, mc, loadboard, carrier_ask, agreed, rounds, ts))
        interactions.append(_interaction(mc, name, call_id, load_id, "booked", duration, ts))

    # ── FAILED calls ─────────────────────────────────────────────────────────
    for row in _FAILED:
        (
            cidx, load_id, origin, dest, equip, miles,
            loadboard, carrier_ask, agent_r2, agent_r3,
            days_ago, hour, minute, duration, rounds, sentiment,
        ) = row

        carrier = _C[cidx]
        mc = carrier["mc"]
        name = carrier["name"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)
        mid = agent_r2
        r2_carrier = round(agent_r2 * 1.08 / 5) * 5

        try:
            transcript = T_FAILED_PRICE.format(
                mc=mc, origin=origin, dest=dest,
                equip=equip.replace("_", " "), miles=miles,
                loadboard=loadboard, carrier_ask=carrier_ask,
                r2=agent_r2, r2_carrier=r2_carrier,
                r3=agent_r3 if agent_r3 else agent_r2,
            )
        except KeyError:
            transcript = T_FAILED_PRICE

        summary = (
            f"Carrier called on {origin} to {dest} {equip.replace('_', ' ')}. "
            f"Carrier opened at ${carrier_ask:,.0f}, broker held near "
            f"${loadboard:,.0f}. Gap too wide — no deal after {rounds} rounds."
        )
        key_points = [
            f"Carrier opened at ${carrier_ask:,.0f} vs ${loadboard:,.0f} posted rate",
            f"Broker's final offer: ${agent_r3 if agent_r3 else agent_r2:,.0f}",
            "No agreement — carrier rate expectations exceeded acceptable ceiling",
        ]

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": name,
            "lane_origin": origin, "lane_destination": dest,
            "equipment_type": equip, "load_id": load_id,
            "initial_rate": float(carrier_ask), "final_rate": None,
            "negotiation_rounds": rounds,
            "carrier_phone": carrier["phone"],
            "special_requests": None, "outcome": "negotiation_failed",
            "sentiment": sentiment, "duration_seconds": duration,
            "transcript": transcript, "summary": summary,
            "key_points": json.dumps(key_points), "created_at": ts,
        })

        offers.extend(_build_offers_failed(call_id, load_id, mc, loadboard, carrier_ask, agent_r2, agent_r3, rounds, ts))
        interactions.append(_interaction(mc, name, call_id, load_id, "negotiation_failed", duration, ts))

    # ── NO-LOADS calls ────────────────────────────────────────────────────────
    for row in _NO_LOADS:
        cidx, origin, equip, direction, days_ago, hour, minute, duration = row
        carrier = _C[cidx]
        mc = carrier["mc"]
        name = carrier["name"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)

        try:
            transcript = T_NO_LOADS.format(
                mc=mc, origin=origin,
                equip=equip.replace("_", " "), direction=direction,
            )
        except KeyError:
            transcript = T_NO_LOADS

        summary = (
            f"Carrier called looking for {equip.replace('_', ' ')} loads out of {origin} "
            f"heading {direction}. No matching loads available at time of call."
        )
        key_points = [
            f"Carrier had {equip.replace('_', ' ')} available out of {origin}",
            f"Requested direction: {direction}",
            "No matching loads found — carrier info noted for follow-up",
        ]

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": name,
            "lane_origin": origin, "lane_destination": None,
            "equipment_type": equip, "load_id": None,
            "initial_rate": None, "final_rate": None,
            "negotiation_rounds": 0,
            "carrier_phone": carrier["phone"],
            "special_requests": None, "outcome": "no_loads_available",
            "sentiment": "neutral", "duration_seconds": duration,
            "transcript": transcript, "summary": summary,
            "key_points": json.dumps(key_points), "created_at": ts,
        })
        interactions.append(_interaction(mc, name, call_id, None, "no_loads_available", duration, ts))

    # ── INVALID CARRIER calls ─────────────────────────────────────────────────
    for row in _INVALID_CALLS:
        inv_idx, reason, days_ago, hour, minute, duration = row
        inv = _INVALID[inv_idx]
        mc = inv["mc"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)

        try:
            transcript = T_INVALID.format(mc=mc, reason=reason)
        except KeyError:
            transcript = T_INVALID

        summary = f"Carrier MC {mc} failed FMCSA verification — {reason}. Call ended without booking."
        key_points = [
            f"FMCSA check returned: {reason}",
            "Carrier directed to resolve status via fmcsa.dot.gov",
            "Call ended — no loads presented",
        ]

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": None,
            "lane_origin": None, "lane_destination": None,
            "equipment_type": None, "load_id": None,
            "initial_rate": None, "final_rate": None,
            "negotiation_rounds": 0,
            "carrier_phone": inv["phone"],
            "special_requests": None, "outcome": "invalid_carrier",
            "sentiment": "neutral", "duration_seconds": duration,
            "transcript": transcript, "summary": summary,
            "key_points": json.dumps(key_points), "created_at": ts,
        })
        # No carrier interaction logged — carrier not eligible

    # ── CARRIER THINKING calls ────────────────────────────────────────────────
    for row in _THINKING:
        (
            cidx, load_id, origin, dest, equip, miles,
            loadboard, carrier_ask,
            days_ago, hour, minute, duration,
        ) = row

        carrier = _C[cidx]
        mc = carrier["mc"]
        name = carrier["name"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)
        mid = round((carrier_ask + loadboard) / 2 / 5) * 5

        try:
            transcript = T_THINKING.format(
                mc=mc, carrier=name, origin=origin, dest=dest,
                equip=equip.replace("_", " "), miles=miles,
                loadboard=loadboard, carrier_ask=carrier_ask, mid=mid,
            )
        except KeyError:
            transcript = T_THINKING

        summary = (
            f"Carrier called on {origin} to {dest} {equip.replace('_', ' ')}. "
            f"Negotiation started but carrier needed to check with dispatcher. "
            f"Call ended without commitment — awaiting callback."
        )
        key_points = [
            f"Carrier's ask: ${carrier_ask:,.0f} — broker countered ${mid:,.0f}",
            "Carrier needed dispatcher approval before committing",
            "Load held pending carrier callback",
        ]

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": name,
            "lane_origin": origin, "lane_destination": dest,
            "equipment_type": equip, "load_id": load_id,
            "initial_rate": float(carrier_ask), "final_rate": None,
            "negotiation_rounds": 1,
            "carrier_phone": carrier["phone"],
            "special_requests": None, "outcome": "carrier_thinking",
            "sentiment": "neutral", "duration_seconds": duration,
            "transcript": transcript, "summary": summary,
            "key_points": json.dumps(key_points), "created_at": ts,
        })

        offers.extend(_build_offers_thinking(call_id, load_id, mc, loadboard, carrier_ask, ts))
        interactions.append(_interaction(mc, name, call_id, load_id, "carrier_thinking", duration, ts))

    # ── TRANSFERRED TO OPS calls ──────────────────────────────────────────────
    for row in _TRANSFERRED:
        cidx, load_id, weight, days_ago, hour, minute, duration = row
        carrier = _C[cidx]
        mc = carrier["mc"]
        name = carrier["name"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)

        try:
            transcript = T_TRANSFERRED.format(mc=mc, weight=weight)
        except KeyError:
            transcript = T_TRANSFERRED

        summary = (
            f"Carrier called with permit/weight question for load {load_id} "
            f"({weight:,} lbs). Escalated to ops team per protocol."
        )
        key_points = [
            f"Load weight {weight:,} lbs — near or at overweight threshold",
            "Carrier raised permitting question agent could not answer",
            "Escalated to ops desk per safety protocol",
        ]

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": name,
            "lane_origin": None, "lane_destination": None,
            "equipment_type": None, "load_id": load_id,
            "initial_rate": None, "final_rate": None,
            "negotiation_rounds": 0,
            "carrier_phone": carrier["phone"],
            "special_requests": f"Weight {weight:,} lbs — permit question raised",
            "outcome": "transferred_to_ops",
            "sentiment": "neutral", "duration_seconds": duration,
            "transcript": transcript, "summary": summary,
            "key_points": json.dumps(key_points), "created_at": ts,
        })
        interactions.append(_interaction(mc, name, call_id, load_id, "transferred_to_ops", duration, ts))

    # ── DROPPED CALL calls ────────────────────────────────────────────────────
    for row in _DROPPED:
        cidx, load_id, days_ago, hour, minute, duration = row
        carrier = _C[cidx]
        mc = carrier["mc"]
        name = carrier["name"]
        call_id = _cid()
        row_id = _uid()
        ts = _ts(days_ago, hour, minute)

        calls.append({
            "id": row_id, "call_id": call_id,
            "mc_number": mc, "carrier_name": name,
            "lane_origin": None, "lane_destination": None,
            "equipment_type": None, "load_id": load_id,
            "initial_rate": None, "final_rate": None,
            "negotiation_rounds": 0,
            "carrier_phone": carrier["phone"],
            "special_requests": None, "outcome": "dropped_call",
            "sentiment": "neutral", "duration_seconds": duration,
            "transcript": T_DROPPED, "summary": "Call dropped before negotiation could begin.",
            "key_points": json.dumps(["Connection lost early in call",
                                      "No load presented — carrier did not call back"]),
            "created_at": ts,
        })
        interactions.append(_interaction(mc, name, call_id, load_id, "dropped_call", duration, ts))

    return calls, offers, interactions


# ─── Booking applier (always runs on startup) ─────────────────────────────────


def _apply_bookings() -> None:
    """Re-insert booked_loads and re-mark load statuses.
    Must run after seed_loads() which wipes booked_loads on every startup."""

    rows = []
    for b in _BOOKED:
        (
            load_id, origin, dest, equip, miles,
            loadboard, carrier_ask, agreed,
            cidx, days_ago, hour, minute, duration,
            rounds, sentiment, tx_key, summary, key_points,
        ) = b
        carrier = _C[cidx]
        ts = _ts(days_ago, hour, minute)
        rows.append({
            "id": _uid(),
            "load_id": load_id,
            "mc_number": carrier["mc"],
            "carrier_name": carrier["name"],
            "agreed_rate": float(agreed),
            "agreed_pickup_datetime": None,
            "offer_id": None,
            "call_id": None,   # cross-linked after call insert
            "created_at": ts,
            "booked_at": ts,
        })

    with get_db() as conn:
        for r in rows:
            conn.execute(
                """INSERT INTO booked_loads
                   (id, load_id, mc_number, carrier_name, agreed_rate,
                    agreed_pickup_datetime, offer_id, call_id, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(id) DO NOTHING""",
                (
                    r["id"], r["load_id"], r["mc_number"], r["carrier_name"],
                    r["agreed_rate"], r["agreed_pickup_datetime"],
                    r["offer_id"], r["call_id"], r["created_at"],
                ),
            )
            conn.execute(
                "UPDATE loads SET status='booked', booked_at=? WHERE load_id=?",
                (r["booked_at"], r["load_id"]),
            )


# ─── Main entry point ─────────────────────────────────────────────────────────


def seed_historical_data() -> None:
    """Wipe and re-seed all demo data on every startup.

    Timestamps are anchored to today so the dashboard always shows
    recent activity regardless of when the server was last restarted.
    """
    global _BASE, _COUNTER

    # Anchor all timestamps to today at midnight UTC
    _BASE = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    _COUNTER = 0  # Reset for deterministic IDs

    # Wipe previous seed data
    with get_db() as conn:
        conn.execute("DELETE FROM carrier_interactions")
        conn.execute("DELETE FROM offers")
        conn.execute("DELETE FROM calls")

    # Re-apply bookings (seed_loads already wiped booked_loads)
    _apply_bookings()

    # Re-build and insert calls, offers, interactions
    calls, offers, interactions = _build_data()

    with get_db() as conn:
        conn.executemany(
            """INSERT INTO calls
               (id, call_id, mc_number, carrier_name, lane_origin, lane_destination,
                equipment_type, load_id, initial_rate, final_rate, negotiation_rounds,
                carrier_phone, special_requests, outcome, sentiment, duration_seconds,
                transcript, summary, key_points, created_at)
               VALUES
               (:id,:call_id,:mc_number,:carrier_name,:lane_origin,:lane_destination,
                :equipment_type,:load_id,:initial_rate,:final_rate,:negotiation_rounds,
                :carrier_phone,:special_requests,:outcome,:sentiment,:duration_seconds,
                :transcript,:summary,:key_points,:created_at)""",
            calls,
        )
        conn.executemany(
            """INSERT INTO offers
               (offer_id, call_id, load_id, mc_number, offer_amount, offer_type,
                round_number, status, notes, created_at, original_rate,
                rate_difference, rate_difference_pct, original_pickup_datetime,
                agreed_pickup_datetime, pickup_changed)
               VALUES
               (:offer_id,:call_id,:load_id,:mc_number,:offer_amount,:offer_type,
                :round_number,:status,:notes,:created_at,:original_rate,
                :rate_difference,:rate_difference_pct,:original_pickup_datetime,
                :agreed_pickup_datetime,:pickup_changed)""",
            offers,
        )
        conn.executemany(
            """INSERT INTO carrier_interactions
               (id, mc_number, carrier_name, call_id, call_length_seconds,
                outcome, load_id, notes, created_at)
               VALUES
               (:id,:mc_number,:carrier_name,:call_id,:call_length_seconds,
                :outcome,:load_id,:notes,:created_at)""",
            interactions,
        )

    print(
        f"   History   : {len(calls)} calls, {len(offers)} offers, "
        f"{len(interactions)} interactions seeded"
    )
