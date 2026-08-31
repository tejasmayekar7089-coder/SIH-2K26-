import os
import secrets
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from app.schemas.document import ValidatedInputDocument
from app.utils.file_utils import detect_file_format, get_mime_type, save_uploaded_bytes
from app.utils.hashing import hash_bytes
from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(prefix="/upload", tags=["Module 1: Ingestion & Upload"])
logger = get_logger("upload_route")

@router.post("", response_model=ValidatedInputDocument)
async def upload_document(
    document_file: UploadFile = File(..., description="Document file (PDF, JPG, PNG, TIFF, WebP)"),
    live_traveller_file: UploadFile = File(None, description="Optional live traveller camera selfie image")
):
    """Module 1: Ingests, validates format/size, and prepares document for screening."""
    # 1. Read document bytes
    doc_bytes = await document_file.read()
    if len(doc_bytes) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    file_format = detect_file_format(document_file.filename)
    mime_type = get_mime_type(file_format)
    checksum = hash_bytes(doc_bytes)
    
    doc_id = f"DOC-{secrets.token_hex(4).upper()}"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{document_file.filename}")
    save_uploaded_bytes(doc_bytes, save_path)

    # 2. Handle optional live traveller photo
    live_image_path = None
    has_live_image = False
    if live_traveller_file:
        live_bytes = await live_traveller_file.read()
        live_image_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_live_{live_traveller_file.filename}")
        save_uploaded_bytes(live_bytes, live_image_path)
        has_live_image = True

    logger.info(f"Ingested document {doc_id} ({document_file.filename}, {len(doc_bytes)} bytes)")

    return ValidatedInputDocument(
        document_id=doc_id,
        file_name=document_file.filename,
        file_format=file_format,
        mime_type=mime_type,
        file_size_bytes=len(doc_bytes),
        sha256_checksum=checksum,
        storage_path=save_path,
        has_live_traveller_image=has_live_image,
        live_image_path=live_image_path
    )
