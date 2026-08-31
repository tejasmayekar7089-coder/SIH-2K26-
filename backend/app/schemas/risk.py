from enum import Enum
from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from app.schemas.common import SeverityLevel

class RiskLevel(str, Enum):
    CLEAR = "CLEAR"         # 0 - 29
    REVIEW = "REVIEW"       # 30 - 69
    HIGH_RISK = "HIGH_RISK" # 70 - 100

class ReasonCode(BaseModel):
    code: str
    description: str
    severity: SeverityLevel
    module_source: str
    weight: int

class RiskAssessment(BaseModel):
    risk_score: int = Field(..., ge=0, le=100, description="Deterministic 0-100 composite risk score")
    risk_level: RiskLevel
    reason_codes: List[ReasonCode] = Field(default_factory=list)
    top_reasons: List[str] = Field(default_factory=list)
    
    # Sub-dimension breakdown
    authenticity_score: int = 0 # 0-100
    validity_score: int = 0     # 0-100
    identity_score: int = 0     # 0-100
    
    requires_manual_inspection: bool = False
    decision_engine_type: str = "CONFIGURABLE_RULE_MATRIX_NOT_LLM"
