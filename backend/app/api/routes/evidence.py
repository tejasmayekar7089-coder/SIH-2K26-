from fastapi import APIRouter
from app.schemas.evidence import EvidenceBundle

router = APIRouter(prefix="/evidence", tags=["Module 10: Common Evidence Schema"])

@router.get("/schema-info")
async def get_evidence_schema_info():
    """Describes Common Evidence Schema and rules."""
    return {
        "schema_name": "UnifiedEvidenceBundle",
        "fields": ["source_module", "data", "confidence (0-1)", "strength (0-1)", "severity", "provenance", "timestamp_utc"],
        "principle": "No single model has authority."
    }
