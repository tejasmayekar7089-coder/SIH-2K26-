from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.schemas.screening import OfficerAction
from app.schemas.risk import RiskLevel

class OfficerAdjudicationRequest(BaseModel):
    officer_id: str
    decision: OfficerAction
    justification_notes: str
    override_ai_recommendation: bool = False

class AuditLogEntry(BaseModel):
    audit_id: str
    screening_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # System Versions
    app_version: str
    model_checkpoints: Dict[str, str] = Field(default_factory=dict)
    
    # Raw & Computed Hashes
    document_sha256: str
    evidence_bundle_hash: str
    
    # Outcomes
    ai_risk_level: RiskLevel
    ai_risk_score: int
    active_hypotheses: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    
    # Human Decisions
    officer_id: Optional[str] = None
    officer_action: OfficerAction = OfficerAction.PENDING
    officer_notes: Optional[str] = None
    processing_time_ms: float = 0.0
