from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.document import DocumentCategory, QualityResult
from app.schemas.extraction import ExtractionResult
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import ValidationResult
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
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Common Evidence items")
    errors_or_warnings: List[str] = Field(default_factory=list, description="Execution notices, warnings, or errors")
