from enum import Enum
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class MetadataClassification(str, Enum):
    SUPPORTING = "SUPPORTING"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    SUSPICIOUS_METADATA = "SUSPICIOUS_METADATA"

class MetadataResult(BaseModel):
    file_type: str
    mime_type: str = "application/octet-stream"
    file_size_bytes: int
    has_exif: bool = False
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    creation_date: Optional[str] = None
    modification_date: Optional[str] = None
    software_signature: Optional[str] = None
    device_make: Optional[str] = None
    device_model: Optional[str] = None
    exif_raw_tags: Dict[str, Any] = Field(default_factory=dict)
    
    # Forensic interpretation
    metadata_classification: MetadataClassification = MetadataClassification.NOT_AVAILABLE
    has_editing_signature: bool = False
    is_recompressed: bool = False
    supporting_notes: str = "Supporting evidence only. Missing, clean, or stripped EXIF is NOT proof of fraud."
