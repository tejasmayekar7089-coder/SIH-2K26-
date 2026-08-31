from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.schemas.document import ValidatedInputDocument
from app.schemas.evidence import EvidenceBundle
from app.schemas.hypothesis import HypothesisResult
from app.schemas.risk import RiskAssessment

class ScreeningStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class OfficerAction(str, Enum):
    PENDING = "PENDING"
    ACCEPT_CLEAR = "ACCEPT_CLEAR"
    SEND_TO_SECONDARY_REVIEW = "SEND_TO_SECONDARY_REVIEW"
    REJECT_FRAUD = "REJECT_FRAUD"

class ScreeningResponse(BaseModel):
    screening_id: str
    status: ScreeningStatus
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processing_time_ms: float = 0.0
    
    # Core results
    document_info: Optional[ValidatedInputDocument] = None
    risk_assessment: Optional[RiskAssessment] = None
    hypothesis_result: Optional[HypothesisResult] = None
    evidence_bundle: Optional[EvidenceBundle] = None
    
    officer_action_state: OfficerAction = OfficerAction.PENDING
    officer_statement: str = "AI ASSISTS • OFFICER DECIDES"
