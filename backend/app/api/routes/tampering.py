import os
import shutil
import uuid
from typing import Optional
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.schemas.tampering import TamperResult
from app.schemas.document import ValidatedInputDocument
from app.modules.tampering.service import TamperingAIService
from app.core.config import settings

router = APIRouter(prefix="/tampering", tags=["Module 6: Tampering AI (Core AI Innovation)"])
tamper_service = TamperingAIService()

@router.post("/inspect", response_model=TamperResult)
async def inspect_tampering(doc_input: ValidatedInputDocument):
    """Standalone Tampering AI analysis endpoint accepting ValidatedInputDocument."""
    return tamper_service.analyze_tampering(doc=doc_input, image_input=doc_input.storage_path)

@router.post("/inspect-file", response_model=TamperResult)
async def inspect_tampering_file(file: UploadFile = File(...)):
    """Standalone Tampering AI analysis endpoint accepting direct file upload."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing")

    temp_id = f"TMP-{uuid.uuid4().hex[:8].upper()}"
    temp_path = os.path.join(settings.UPLOAD_DIR, f"{temp_id}_{file.filename}")

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = tamper_service.analyze_tampering(image_input=temp_path)
        return result
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass

