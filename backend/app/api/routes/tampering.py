from fastapi import APIRouter
from app.schemas.tampering import TamperResult
from app.schemas.document import ValidatedInputDocument
from app.modules.tampering.service import TamperingAIService

router = APIRouter(prefix="/tampering", tags=["Module 6: Tampering AI (Core AI Innovation)"])
tamper_service = TamperingAIService()

@router.post("/inspect", response_model=TamperResult)
async def inspect_tampering(doc_input: ValidatedInputDocument):
    """Standalone Tampering AI analysis endpoint with DocTamper and TruFor fallback."""
    return tamper_service.analyze_tampering(doc_input, doc_input.storage_path)
