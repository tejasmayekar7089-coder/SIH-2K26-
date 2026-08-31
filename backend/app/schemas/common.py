from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SeverityLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class DecisionDimension(str, Enum):
    AUTHENTICITY = "AUTHENTICITY"
    VALIDITY = "VALIDITY"
    IDENTITY = "IDENTITY"

class BoundingBox(BaseModel):
    x: int = Field(..., description="Top left X coordinate")
    y: int = Field(..., description="Top left Y coordinate")
    width: int = Field(..., description="Width of bounding box")
    height: int = Field(..., description="Height of bounding box")

class EvidenceItem(BaseModel):
    """Unified evidence schema standard for all modules."""
    source_module: str = Field(..., description="Originating module ID (e.g. DOCUMENT_INTELLIGENCE, MRZ_PROCESSING, METADATA_ANALYSIS)")
    data: Dict[str, Any] = Field(default_factory=dict, description="Structured module signal data")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Statistical model confidence")
    strength: float = Field(..., ge=0.0, le=1.0, description="Weight/reliability of signal")
    severity: SeverityLevel = Field(..., description="Anomaly grade")
    provenance: str = Field(..., description="Model version, checkpoint, algorithm signature")
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="ISO 8601 UTC timestamp")
    bbox: Optional[List[int]] = Field(default=None, description="[x1, y1, x2, y2] bounding box coordinates")
    reason_code: Optional[str] = Field(default=None, description="Explicit reason code if applicable")

    def to_field_evidence_dict(self) -> Dict[str, Any]:
        """Serializes EvidenceItem into standardized field evidence format."""
        sev_val = self.severity.value if isinstance(self.severity, Enum) else str(self.severity)
        field_name = self.data.get("field") or self.data.get("field_name") or "unknown_field"
        extracted_val = self.data.get("value") if "value" in self.data else self.data.get("data", "")
        
        return {
            "field": field_name,
            "data": extracted_val,
            "confidence": self.confidence,
            "strength": self.strength,
            "severity": sev_val,
            "provenance": self.provenance,
            "bbox": self.bbox,
            "reason_code": self.reason_code
        }
