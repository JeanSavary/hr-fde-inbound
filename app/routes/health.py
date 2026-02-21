from fastapi import APIRouter
from app.config import get_settings

router = APIRouter()


@router.get("/health", tags=["Health"])
async def health():
    s = get_settings()
    return {
        "status": "healthy",
        "service": s.app_name,
        "fmcsa_mode": "live" if s.fmcsa_web_key else "mock",
    }
