# Acme Logistics — Carrier Inbound Sales API

FastAPI backend for the HappyRobot voice agent demo. Handles carrier authentication,
load search (city/state/region, alternatives with pitch-ready differences), negotiation
logging, and dashboard analytics.

## Quick Start

```bash
# 1. Clone / cd into project
cd happy-robot

# 2. Install dependencies (uv)
uv sync --group dev

# 3. Optional: copy .env.example and edit for production
# cp .env.example .env

# 4. Run server
uv run uvicorn app.main:app --reload

# 5. Test everything
uv run python test_api.py
```

Server starts at **http://localhost:8000**
Swagger docs at **http://localhost:8000/docs**

### Dev

```bash
uv run ruff format app    # format code
uv run ruff check app     # lint
```

### With Docker

```bash
docker-compose up --build
```

---

## Authentication

All `/api/*` endpoints require:

```
X-API-Key: dev-api-key-change-me
```

---

## Endpoints

| Method | Endpoint               | Purpose                                       |
| ------ | ---------------------- | --------------------------------------------- |
| GET    | `/health`              | Health check (no auth)                        |
| POST   | `/api/carriers/verify` | Business eligibility check                    |
| GET    | `/api/loads/search`    | Load search (city/state/region, alternatives) |
| GET    | `/api/loads/{load_id}` | Single load details                           |

*Offers, Calls, and Dashboard endpoints exist but are hidden from Swagger docs.*

---

## Mock Carriers for Demo

| MC Number  | Carrier              | Status         | Outcome     |
| ---------- | -------------------- | -------------- | ----------- |
| **123456** | Swift Haul Logistics | Active, clean  | ✅ Eligible |
| **789012** | Heartland Express    | Active, clean  | ✅ Eligible |
| **456789** | Cold Chain Carriers  | Active, clean  | ✅ Eligible |
| **111111** | Defunct Trucking Co  | Inactive       | ❌ Rejected |
| **222222** | Risky Freight LLC    | Out of Service | ❌ Rejected |
| **333333** | New Carrier Pending  | No authority   | ❌ Rejected |
| **999999** | (any other)          | Not found      | ❌ Rejected |

---

## Seed Loads

51 loads across major US freight corridors (from `data/loads.json`). Equipment types: Dry Van, Reefer, Flatbed, Step Deck, Power Only.

| ID      | Lane                                    | Equipment  | Rate   |
| ------- | --------------------------------------- | ---------- | ------ |
| LD-1001 | Dallas → Chicago                        | Dry Van    | $2,150 |
| LD-1002 | Atlanta → Miami                         | Reefer     | $1,850 |
| LD-1004 | Houston → Memphis                       | Dry Van    | $1,420 |
| LD-1008 | Newark → Boston                         | Reefer     | $680   |
| LD-1024 | Columbus → Buffalo                      | Dry Van    | $820   |
| LD-1031 | Atlanta → Dallas                        | Dry Van    | $1,950 |
| LD-1037 | Houston → Memphis                       | Dry Van    | $1,550 |
| LD-1042 | Houston → Dallas                        | Step Deck  | $980   |
| LD-1047 | Dallas → Houston                        | Power Only | $550   |
| …       | _(see `data/loads.json` for full list)_ |            |        |

---

## Load Search Features

The `/api/loads/search` endpoint supports flexible origin/destination and returns enriched load data.

### Origin & Destination: City, State, or Region

| Input type | Examples                                                                                            |
| ---------- | --------------------------------------------------------------------------------------------------- |
| **City**   | `Dallas`, `Dallas, TX`, `Houston`, `Chicago`                                                        |
| **State**  | `TX`, `Texas`, `CA`, `California`                                                                   |
| **Region** | `South Central`, `West Coast`, `Midwest`, `Northeast`, `Southeast`, `Great Plains`, `Mountain West` |

Examples: `origin=TX&destination=Northeast`, `origin=South Central&destination=Houston`

### Response Enrichment

Each load includes:

- **`rate_per_mile`** — `loadboard_rate ÷ miles`
- **`deadhead_miles`** — Distance from requested origin to load pickup (0 if origin is state/region)
- **`deadend_miles`** — Distance from load delivery to requested destination (0 if none or state/region)

### Alternative Loads

When fewer than 3 strict matches are found, up to 5 **alternative_loads** are returned. Each has a `differences` array explaining what doesn’t match (e.g. equipment type, pickup location, destination). Total results (strict + alternatives) never exceed 5.

### Geo Resolution

- **Fuzzy matching**: "dalas" → Dallas, TX
- **Aliases**: "DFW", "ATL", "Chi-town", "H-town", "the Bay"
- **Prefix strips**: "near Dallas", "around Houston", "Dallas area"
- **Radius search**: 75mi default (configurable) for city-based queries
- **Nominatim fallback**: Unknown cities geocoded on-the-fly

---

## Negotiation Boundaries

The `/api/offers` endpoint returns `rate_floor` and `rate_ceiling` with every offer:

- **Floor** = `loadboard_rate × 0.90` (lowest acceptable)
- **Ceiling** = `loadboard_rate × 1.10` (auto-reject above this)
- Configurable via `RATE_FLOOR_PERCENT` and `RATE_CEILING_PERCENT` in `.env`

---

## Environment Variables

| Variable                      | Default                 | Description                    |
| ----------------------------- | ----------------------- | ------------------------------ |
| `API_KEY`                     | `dev-api-key-change-me` | API authentication key         |
| `FMCSA_WEB_KEY`               | _(empty = mock)_        | FMCSA API key for live lookups |
| `BROKERAGE_NAME`              | Acme Logistics          | Company name for prompts       |
| `AGENT_NAME`                  | John                    | Agent persona name             |
| `DEFAULT_SEARCH_RADIUS_MILES` | 75                      | Geo search radius              |
| `RATE_FLOOR_PERCENT`          | 0.90                    | Minimum rate (× loadboard)     |
| `RATE_CEILING_PERCENT`        | 1.10                    | Maximum rate (× loadboard)     |
| `MAX_NEGOTIATION_ROUNDS`      | 3                       | Rounds before final offer      |

---

## Project Structure

```
happy-robot/
├── app/
│   ├── config.py              # Settings from .env
│   ├── main.py                # FastAPI app, lifespan, routes
│   ├── models/                # Pydantic schemas (load, carrier, offer, call)
│   ├── routes/                # API endpoints (health, carriers, loads, etc.)
│   ├── services/              # Business logic (carrier, load, call)
│   ├── db/
│   │   ├── schema.py          # Table definitions
│   │   ├── seed.py            # Cities + loads seeding
│   │   ├── city_data.py       # 363 US cities with state/region metadata
│   │   ├── connection.py      # SQLite connection
│   │   └── repositories/      # Data access layer
│   └── utils/
│       ├── geo.py             # City/state/region resolution, haversine, Nominatim
│       └── fmcsa.py           # FMCSA lookup (used by carriers/verify)
├── data/
│   ├── loads.json            # Seed load data
│   └── carrier.db            # SQLite (auto-created)
├── pyproject.toml            # uv dependencies, ruff config
├── .env                      # Environment config
├── Dockerfile
└── docker-compose.yml
```
