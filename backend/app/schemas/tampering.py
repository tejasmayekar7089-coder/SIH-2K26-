from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator
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
    tamper_score: float = Field(..., ge=0.0, le=1.0, description="Overall document tampering score")
    status: str = Field(default="CLEAR", description="Verdict string: TAMPERED or CLEAR")
    severity: str = Field(default="LOW", description="LOW, MEDIUM, or HIGH")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence for the tampering verdict")
    regions: List[SuspiciousRegion] = Field(default_factory=list, description="Structured list of anomalous regions")
    is_tampered: bool = False

    # Forensic maps
    heatmap_image_path: Optional[str] = None
    mask_image_path: Optional[str] = None

    suspicious_regions: List[SuspiciousRegion] = Field(default_factory=list)
    fallback_invoked: bool = False
    fallback_reason: Optional[str] = None

    @model_validator(mode="after")
    def sync_structured_output(self):
        if self.regions:
            self.suspicious_regions = self.regions
        elif self.suspicious_regions:
            self.regions = self.suspicious_regions

        if self.confidence == 0.0:
            self.confidence = float(round(min(max(self.tamper_score, 0.0), 1.0), 4))

        self.status = "TAMPERED" if self.is_tampered else "CLEAR"
        if self.is_tampered:
            if self.tamper_score >= 0.75:
                self.severity = "HIGH"
            elif self.tamper_score >= 0.45:
                self.severity = "MEDIUM"
            else:
                self.severity = "LOW"
        else:
            self.severity = "LOW"

        return self
