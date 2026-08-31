import os
import secrets
import io
from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from PIL import Image

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False

from app.schemas.document import FileFormat
from app.schemas.pipeline import DocumentProcessingResult
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.utils.file_utils import detect_file_format, get_mime_type, save_uploaded_bytes
from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(prefix="/documents", tags=["Developer 1: Document Intelligence API"])
logger = get_logger("documents_route")

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tiff", ".pdf"}

@router.post("/analyze", response_model=DocumentProcessingResult)
async def analyze_document(
    document_file: Optional[UploadFile] = File(None, description="Document image or PDF file (JPG, PNG, WEBP, TIFF, PDF)"),
    file: Optional[UploadFile] = File(None, description="Document file alias")
):
    """
    Developer 1 Document Intelligence Pipeline Endpoint:
    Upload -> Quality -> Classification -> OCR -> Extraction -> MRZ (Passports) -> Metadata -> Validation -> Evidence
    Returns structured DocumentProcessingResult.
    """
    upload_file = document_file or file
    if not upload_file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No document file uploaded in request payload."
        )

    filename = upload_file.filename or "uploaded_document"
    ext = os.path.splitext(filename)[1].lower()

    logger.info(f"Received document analyze request: {filename} (Ext: {ext})")

    # 1. Format Validation (400 Bad Request)
    if ext not in SUPPORTED_EXTENSIONS:
        logger.warning(f"Rejected unsupported file format: {ext} for file {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Supported formats: JPG, JPEG, PNG, WEBP, TIFF, PDF."
        )

    # 2. File Size Validation (413 Payload Too Large)
    doc_bytes = await upload_file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(doc_bytes) > max_bytes:
        logger.warning(f"Rejected oversized file upload: {len(doc_bytes)} bytes > max {max_bytes} bytes")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    if len(doc_bytes) == 0:
        logger.warning(f"Rejected empty 0-byte file: {filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    # 3. Payload Integrity / Corruption Check (400 Bad Request)
    if ext in {".jpg", ".jpeg", ".png", ".webp", ".tiff"}:
        try:
            with Image.open(io.BytesIO(doc_bytes)) as img:
                img.verify()
        except Exception as e:
            logger.warning(f"Corrupted image payload detected for {filename}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Corrupted or unreadable image file: {e}"
            )
    elif ext == ".pdf":
        if HAS_FITZ:
            try:
                doc_fitz = fitz.open(stream=doc_bytes, filetype="pdf")
                if doc_fitz.page_count < 1:
                    raise ValueError("PDF contains 0 pages.")
                doc_fitz.close()
            except Exception as e:
                logger.warning(f"Corrupted PDF payload detected for {filename}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Corrupted or invalid PDF file: {e}"
                )

    # 4. Save Payload & Execute Pipeline
    doc_id = f"DOC-{secrets.token_hex(4).upper()}"
    save_path = os.path.join(settings.UPLOAD_DIR, f"{doc_id}_{filename}")

    try:
        save_uploaded_bytes(doc_bytes, save_path)
    except Exception as e:
        logger.error(f"Failed to persist file payload to disk: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage error: Failed to persist file payload."
        )

    # 5. Run Unified Pipeline
    try:
        pipeline = DocumentIntelligencePipeline()
        result = pipeline.process_document(file_path=save_path, document_id=doc_id)
        return result
    except Exception as e:
        logger.error(f"Unhandled document pipeline error for {doc_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing pipeline error: {e}"
        )
