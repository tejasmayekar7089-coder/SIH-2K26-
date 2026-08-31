from typing import Optional, Dict, Any

class DocumentScreeningException(Exception):
    """Base exception for all document screening pipeline errors."""
    def __init__(self, message: str, module: str = "core", error_code: str = "INTERNAL_ERROR", details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.module = module
        self.error_code = error_code
        self.details = details or {}

class AcquisitionError(DocumentScreeningException):
    """Raised during document ingestion, format parsing or image loading."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="acquisition", error_code="ACQUISITION_FAILED", details=details)

class QualityCheckError(DocumentScreeningException):
    """Raised when document image quality falls below acceptable threshold."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="quality", error_code="QUALITY_UNACCEPTABLE", details=details)

class DocumentIntelligenceError(DocumentScreeningException):
    """Raised during layout parsing, OCR or portrait extraction."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="document_intelligence", error_code="DOC_INTEL_FAILED", details=details)

class MRZParsingError(DocumentScreeningException):
    """Raised when MRZ reading/parsing fails."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="mrz", error_code="MRZ_PARSE_FAILED", details=details)

class TamperingInferenceError(DocumentScreeningException):
    """Raised when tampering AI models fail execution."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="tampering", error_code="TAMPER_INFERENCE_FAILED", details=details)

class FaceVerificationError(DocumentScreeningException):
    """Raised during 1:1 facial biometric extraction or verification."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="face", error_code="FACE_VERIFICATION_FAILED", details=details)

class DatabaseLookupError(DocumentScreeningException):
    """Raised when simulated external intelligence DB encounters an error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, module="external_intelligence", error_code="DB_LOOKUP_FAILED", details=details)
