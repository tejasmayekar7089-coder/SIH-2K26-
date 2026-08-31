from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.common import SeverityLevel

class FieldTamperOverlap(BaseModel):
    field_name: str
    extracted_text: Optional[str] = None
    overlap_ratio: float = Field(..., ge=0.0, le=1.0, description="IoU/Intersection area ratio with tamper mask")
    tamper_risk: SeverityLevel = SeverityLevel.LOW
    reason_code: Optional[str] = None # e.g. TAMPER_OVERLAP_DOB

class FieldMappingResult(BaseModel):
    field_overlaps: List[FieldTamperOverlap] = Field(default_factory=list)
    has_tampered_fields: bool = False
    highest_risk_field: Optional[str] = None
    highest_severity: SeverityLevel = SeverityLevel.LOW
