from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class DocumentCategory(str, Enum):
    PASSPORT = "PASSPORT"
    AADHAAR = "AADHAAR"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    DRIVING_LICENCE = "DRIVING_LICENCE"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
    PERMIT = "PERMIT"
    TRAVEL_DOCUMENT = "TRAVEL_DOCUMENT"
    UNKNOWN = "UNKNOWN"

class FileFormat(str, Enum):
    PDF = "PDF"
    JPG = "JPG"
    JPEG = "JPEG"
    PNG = "PNG"
    TIFF = "TIFF"
    WEBP = "WEBP"

class ValidatedInputDocument(BaseModel):
    document_id: str = Field(..., description="Unique generated ID for document")
    file_name: str
    file_format: FileFormat
    mime_type: str
    file_size_bytes: int
    sha256_checksum: str
    storage_path: str
    has_live_traveller_image: bool = False
    live_image_path: Optional[str] = None

class QualityResult(BaseModel):
    quality_score: float = Field(default=0.85, ge=0.0, le=1.0, description="Overall image quality score e.g. 0.85")
    blur_score: float = Field(default=200.0, description="Laplacian variance blur metric")
    is_blurred: bool = False
    glare_score: float = Field(default=0.0, description="Specular highlight reflection ratio")
    has_glare: bool = False
    resolution_dpi: int = Field(default=300, description="Estimated DPI")
    is_skewed: bool = False
    deskew_angle: float = 0.0
    completeness_score: float = 1.0
    processed_image_path: str = ""
    is_acceptable: bool = True
