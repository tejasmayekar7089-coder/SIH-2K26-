from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.api.router import api_router
from app.database.connection import init_db

logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables and directories
    logger.info("Initializing SIH26188 Screening System Backend...")
    await init_db()
    logger.info(f"System ready on {settings.HOST}:{settings.PORT}")
    yield
    # Shutdown
    logger.info("Shutting down SIH26188 Screening System...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="AI-Based Fake Identity & Document Screening System — Evidence Driven, Explainable, Modular, Officer Decides.",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount outputs for previewing heatmaps & processed images
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
app.mount("/static/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs_static")
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs_direct")

# Include central API router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
async def root():
    return {
        "title": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": f"{settings.API_V1_STR}/health",
        "tenet": "AI ASSISTS • OFFICER DECIDES"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
