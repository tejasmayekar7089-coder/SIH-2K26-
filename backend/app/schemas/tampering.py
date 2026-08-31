from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox

class TamperModelSource(str, Enum):
    DOCTAMPER = "DOCTAMPER_DTD_PRIMARY"
    TRUFOR = "TRUFOR_FALLBACK"
    SYNTHETIC_MOCK = "SYNTHETIC_BENCHMARK_MODEL"

class SuspiciousRegion(BaseModel):
    region_id: str
    bounding_box: BoundingBox
    anomaly_score: float = Field(..., ge=0.0, le=1.0)
    anomaly_type: str = "MANIPULATION" # SPLICING, ERASURE, COPY_MOVE, TEXT_ALTERATION

class TamperResult(BaseModel):
    model_used: TamperModelSource
    is_tampered: bool = False
    tamper_score: float = Field(..., ge=0.0, le=1.0, description="Overall document tampering score")
    
    # Forensic maps
    heatmap_image_path: Optional[str] = None
    mask_image_path: Optional[str] = None
    
    suspicious_regions: List[SuspiciousRegion] = Field(default_factory=list)
    fallback_invoked: bool = False
    fallback_reason: Optional[str] = None
