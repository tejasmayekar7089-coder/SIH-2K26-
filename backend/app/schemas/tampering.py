from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox, EvidenceItem

class TamperModelSource(str, Enum):
    SIGNAL_MULTI_STREAM_ELA_SRM = "SIGNAL_MULTI_STREAM_ELA_SRM"
    DOCTAMPER = "DOCTAMPER_DTD_PRIMARY"
    DOCTAMPER_DTD = "DOCTAMPER_DTD_PRIMARY"
    TRUFOR = "TRUFOR_FALLBACK"
    SYNTHETIC_MOCK = "SYNTHETIC_BENCHMARK_MODEL"

class SuspiciousRegion(BaseModel):
    region_id: str
    bounding_box: BoundingBox
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    anomaly_type: str = "TEXT_MANIPULATION" # TEXT_MANIPULATION, PHOTO_REPLACEMENT, COPY_PASTE, INPAINTING, SPLICING

class TamperResult(BaseModel):
    model_used: TamperModelSource = TamperModelSource.SIGNAL_MULTI_STREAM_ELA_SRM
    model: str = Field(default="SIGNAL_MULTI_STREAM_ELA_SRM", description="Model name or source engine")
    is_tampered: bool = False
    tampering_detected: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Tampering probability/confidence score")
    tamper_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall document tampering score")
    risk_level: str = Field(default="LOW", description="Risk level grade: LOW, MEDIUM, or HIGH")
    tampering_types: List[str] = Field(default_factory=list, description="List of detected tampering anomaly types")
    
    # Forensic maps
    heatmap_available: bool = True
    heatmap_image_path: Optional[str] = None
    mask_image_path: Optional[str] = None
    
    suspicious_regions: List[SuspiciousRegion] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Structured tampering evidence items")
    processing_time_ms: int = Field(default=0, description="Processing duration in milliseconds")
    
    fallback_invoked: bool = False
    fallback_reason: Optional[str] = None

