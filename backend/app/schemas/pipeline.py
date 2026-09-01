from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.document import DocumentCategory, QualityResult
from app.schemas.extraction import ExtractionResult
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import ValidationResult
from app.schemas.tampering import TamperResult
from app.schemas.common import EvidenceItem

class DocumentProcessingResult(BaseModel):
    """Unified Developer 1 Document Intelligence Pipeline Result Schema."""
    document_id: str = Field(..., description="Unique generated document tracking ID")
    document_type: DocumentCategory = Field(default=DocumentCategory.UNKNOWN, description="Classified document category")
    file_info: Dict[str, Any] = Field(default_factory=dict, description="File metadata summary (type, MIME, size)")
    quality: QualityResult
    ocr: OCRResult
    extracted_fields: ExtractionResult
    mrz: Optional[MRZResult] = Field(default=None, description="Parsed TD3 MRZ result if document is a Passport")
    metadata: MetadataResult
    validation: ValidationResult
    tampering: Optional[TamperResult] = Field(default=None, description="Tampering AI analysis result")
    validation_mode: str = Field(default="STRICT", description="Validation mode (STRICT or TEST_FIXTURE)")
    is_synthetic_fixture: bool = Field(default=False, description="Flag indicating if document matched a registered test fixture")
    fixture_info: Optional[Dict[str, Any]] = Field(default=None, description="Metadata of registered fixture if matched")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Common Evidence items")
    tampering: Optional[TamperResult] = Field(default=None, description="Structured tampering detection result")
    errors_or_warnings: List[str] = Field(default_factory=list, description="Execution notices, warnings, or errors")

