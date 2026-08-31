from fastapi import APIRouter
from app.core.config import settings

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("")
async def health_check():
    """System health check and diagnostic probe."""
    return {
        "status": "healthy",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "modules_active": 14,
        "tenet": "AI ASSISTS • OFFICER DECIDES"
    }
