from fastapi import APIRouter
from app.api.routes import health, upload, screening, face, tampering, evidence, doc_intel, documents

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(upload.router)
api_router.include_router(documents.router)
api_router.include_router(doc_intel.router)
api_router.include_router(screening.router)
api_router.include_router(face.router)
api_router.include_router(tampering.router)
api_router.include_router(evidence.router)
