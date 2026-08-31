from abc import ABC, abstractmethod
from typing import Optional, Dict
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.schemas.document import DocumentCategory

class BaseFieldExtractor(ABC):
    """Abstract base class for document field extractors."""

    @abstractmethod
    def extract_fields(self, ocr_result: OCRResult) -> ExtractionResult:
        """Extract structured document fields from OCRResult."""
        pass
