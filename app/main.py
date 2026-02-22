"""
John's Freight — Carrier Inbound Sales API
Built for the John's Freight FDE Technical Challenge.

All /api/* endpoints require header: X-API-Key
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.schema import init_db
from app.db.seed import seed_cities, seed_loads, seed_negotiation_settings
from app.routes import health, carriers, loads, offers, calls, dashboard
from app.routes import carrier_interactions, booked_loads, negotiation_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_cities()
    seed_loads()
    seed_negotiation_settings()
    s = get_settings()
    print(f"✅ {s.app_name} ready")
    print(f"   Brokerage : {s.brokerage_name}")
    print(f"   FMCSA     : {'live' if s.fmcsa_web_key else 'mock mode'}")
    print(f"   Radius    : {s.default_search_radius_miles} mi")
    yield


app = FastAPI(
    title="John's Freight API",
    description="API for John's Freight voice agent — carrier auth, load search, negotiation, analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(carriers.router)
app.include_router(carrier_interactions.router)
app.include_router(loads.router)
app.include_router(offers.router)
app.include_router(calls.router)
app.include_router(booked_loads.router)
app.include_router(dashboard.router)
app.include_router(negotiation_settings.router)
