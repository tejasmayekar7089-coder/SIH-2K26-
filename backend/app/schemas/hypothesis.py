from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import SeverityLevel

class HypothesisType(str, Enum):
    ALTERED_FIELD = "ALTERED_FIELD"
    PHOTO_REPLACEMENT = "PHOTO_REPLACEMENT"
    IMPERSONATION = "IMPERSONATION"
    STATUS_FRAUD = "STATUS_FRAUD"
    UNKNOWN_ANOMALY = "UNKNOWN_ANOMALY"

class FraudHypothesis(BaseModel):
    hypothesis_type: HypothesisType
    title: str
    description: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    severity: SeverityLevel = SeverityLevel.MEDIUM
    supporting_evidence_ids: List[str] = Field(default_factory=list)
    reasoning: str

class HypothesisResult(BaseModel):
    active_hypotheses: List[FraudHypothesis] = Field(default_factory=list)
    has_fraud_suspicions: bool = False
    primary_hypothesis: Optional[HypothesisType] = None
