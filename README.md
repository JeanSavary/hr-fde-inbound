# Carrier Inbound Sales API

FastAPI backend for the HappyRobot voice-agent demo. Handles carrier verification (FMCSA), load search with fuzzy geo-matching, rate negotiation, booking, and analytics.

## Quick Start

### Local (uv)

```bash
cp .env.example .env   # fill in your values
uv sync --group dev
uv run uvicorn app.main:app --reload
```

Server: **http://localhost:8000** | Docs: **http://localhost:8000/docs**

### Docker

```bash
cp .env.example .env   # fill in your values
docker compose up --build
```

### Expose via ngrok (for HappyRobot testing)

Add your `NGROK_AUTHTOKEN` to `.env`, then:

```bash
./scripts/tunnel.sh
```

The public HTTPS URL is printed in the terminal -- paste it into the HappyRobot platform.

---

## Deploy to Railway

1. Push this repo to GitHub.
2. Create a new project on [Railway](https://railway.app) and connect the repo.
3. Add environment variables in the Railway dashboard (see table below).
4. Railway auto-deploys from the `Dockerfile`. The health check hits `/health`.
5. Your public URL is shown in the Railway dashboard under **Settings > Networking > Public Networking**.

---

## Authentication

All `/api/*` endpoints require the header:

```
X-API-Key: <your API_KEY>
```

The `/health` endpoint is public.

---

## Endpoints

| Method | Path                                     | Description                                       |
| ------ | ---------------------------------------- | ------------------------------------------------- |
| GET    | `/health`                                | Health check (no auth)                            |
| POST   | `/api/carriers/verify`                   | Carrier eligibility (FMCSA)                       |
| POST   | `/api/carriers/interactions`             | Log carrier interaction                           |
| GET    | `/api/carriers/{mc_number}/interactions` | Carrier interaction history                       |
| POST   | `/api/loads/search`                      | Search loads (city/state/region)                  |
| GET    | `/api/loads/{load_id}`                   | Single load details                               |
| POST   | `/api/loads/reschedule`                  | Check reschedule feasibility                      |
| POST   | `/api/offers/analyze`                    | Analyze an offer against boundaries (depreciated) |
| POST   | `/api/booked-loads`                      | Book a load                                       |
| GET    | `/api/booked-loads`                      | List bookings                                     |
| GET    | `/api/booked-loads/{load_id}`            | Booking details                                   |
| POST   | `/api/calls`                             | Log a call                                        |
| GET    | `/api/calls`                             | List calls                                        |
| GET    | `/api/calls/{call_id}`                   | Call details                                      |
| GET    | `/api/settings/negotiation`              | Get negotiation settings                          |
| PUT    | `/api/settings/negotiation`              | Update negotiation settings                       |

Full request/response schemas available at `/docs`.

---

## Environment Variables

| Variable                      | Default                 | Description                     |
| ----------------------------- | ----------------------- | ------------------------------- |
| `API_KEY`                     | `dev-api-key-change-me` | API authentication key          |
| `FMCSA_WEB_KEY`               | _(empty = mock)_        | FMCSA API key for live lookups  |
| `BROKERAGE_NAME`              | `Acme Logistics`        | Company name used in prompts    |
| `AGENT_NAME`                  | `John`                  | Agent persona name              |
| `DEFAULT_SEARCH_RADIUS_MILES` | `75`                    | Geo search radius (miles)       |
| `RATE_FLOOR_PERCENT`          | `0.90`                  | Min acceptable rate multiplier  |
| `RATE_CEILING_PERCENT`        | `1.10`                  | Max acceptable rate multiplier  |
| `MAX_NEGOTIATION_ROUNDS`      | `3`                     | Rounds before final offer       |
| `NGROK_AUTHTOKEN`             | _(empty)_               | ngrok token (local tunnel only) |

---

## Load Dataset (`data/loads.json`)

The seed dataset contains **51 loads** for recruiter testing. Use this distribution to choose representative lanes, equipment types, and regions.

### Equipment Type Distribution

| Equipment Type | Count | Share |
| -------------- | ----- | ----- |
| Dry Van        | 23    | 45%   |
| Reefer         | 10    | 20%   |
| Flatbed        | 8     | 16%   |
| Step Deck      | 5     | 10%   |
| Power Only     | 5     | 10%   |

### States / Regions

Loads touch **34 states**. Most represented (by origin + destination frequency):

| State      | Loads  |
| ---------- | ------ |
| TX         | 26     |
| GA         | 8      |
| CA         | 7      |
| TN         | 7      |
| FL         | 6      |
| IL, PA, AZ | 4 each |
| NC, MO     | 3 each |

### Sample Lanes (for testing)

| Lane                          | Count | Notes                            |
| ----------------------------- | ----- | -------------------------------- |
| Atlanta, GA → Miami, FL       | 2     | Reefer / Power Only              |
| Los Angeles, CA → Phoenix, AZ | 2     | Flatbed / Power Only             |
| Houston, TX → Memphis, TN     | 2     | Dry Van                          |
| Dallas, TX → Houston, TX      | 2     | Dry Van / Step Deck / Power Only |
| Dallas, TX → Chicago, IL      | 1     | Dry Van, ~920 mi                 |
| Salinas, CA → Denver, CO      | 1     | Reefer, ~1140 mi                 |

### Cities (54 unique)

**Texas:** Dallas, Fort Worth, Houston, San Antonio, Austin, Laredo, El Paso  
**California:** Los Angeles, Sacramento, Fresno, Bakersfield, Salinas  
**Southeast:** Atlanta, Charlotte, Jacksonville, Miami, Tampa, Orlando, Nashville, Memphis, Birmingham, Savannah  
**Midwest:** Chicago, Detroit, Indianapolis, Columbus, Milwaukee, St. Louis, Kansas City, Omaha, Des Moines, Minneapolis, Wichita  
**Northeast:** Newark, Philadelphia, Pittsburgh, Boston, Baltimore, Harrisburg, Buffalo  
**Southwest:** Phoenix, Tucson, Albuquerque, Las Vegas, Reno  
**Other:** Seattle, Portland, Denver, Salt Lake City, New Orleans, Louisville, Little Rock, Oklahoma City, Richmond

### Miles & Commodity

- **Miles:** 32–1,140 (avg ~363)
- **Commodity types:** 40+ (e.g. Fresh Produce, Frozen Meat, Steel, Lumber, Pharmaceuticals, E-Commerce Goods)

---

## Project Structure

```
app/
├── config.py              # Settings (.env)
├── main.py                # FastAPI app, lifespan, routes
├── prompts.py             # AI prompt templates
├── models/                # Pydantic schemas
├── routes/                # API endpoints + auth middleware
├── services/              # Business logic
├── schemas/               # JSON schemas (LLM structured output)
├── db/
│   ├── schema.py          # Table definitions
│   ├── seed.py            # Data seeding (cities, loads)
│   ├── city_data.py       # 363 US cities with metadata
│   ├── connection.py      # SQLite connection
│   └── repositories/      # Data access layer
└── utils/
    ├── geo.py             # Geo resolution, haversine, fuzzy match
    └── fmcsa.py           # FMCSA carrier lookup
```
