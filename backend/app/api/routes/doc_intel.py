from fastapi import APIRouter, HTTPException, status
from app.schemas.document import ValidatedInputDocument
from app.schemas.extraction import ExtractionResult
from app.schemas.pipeline import DocumentProcessingResult
from app.modules.acquisition.service import AcquisitionService
from app.modules.document_intelligence.service import DocumentIntelligenceService
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.core.logging import get_logger

router = APIRouter(prefix="/document-intelligence", tags=["Developer 1: Document Intelligence & OCR Pipeline"])
logger = get_logger("doc_intel_route")

@router.post("/process", response_model=ExtractionResult)
async def process_document_intelligence(doc_input: ValidatedInputDocument):
    """
    Module 2 + 3 Endpoint: Runs image quality analysis, pre-processing,
    PaddleOCR engine extraction, heuristic classification, and structured field extraction.
    """
    logger.info(f"Processing document intelligence request for doc {doc_input.document_id}")

    acq_service = AcquisitionService()
    quality_result = acq_service.evaluate_and_preprocess(doc_input)

    doc_intel_service = DocumentIntelligenceService()
    extraction_result = doc_intel_service.extract_document_features(
        doc_input,
        image_path=quality_result.processed_image_path
    )

    return extraction_result

@router.post("/pipeline/process", response_model=DocumentProcessingResult)
async def process_unified_pipeline(doc_input: ValidatedInputDocument):
    """
    Developer 1 Unified Pipeline Endpoint: Runs complete process_document() workflow from
    File Validation -> Acquisition -> Quality -> Classification -> OCR -> Field Extraction ->
    MRZ -> Metadata -> Deterministic Validation -> Common Evidence Output.
    """
    logger.info(f"Processing unified document pipeline for doc {doc_input.document_id}")

    pipeline = DocumentIntelligencePipeline()
    result = pipeline.process_document(
        file_path=doc_input.storage_path,
        document_id=doc_input.document_id
    )

    return result
