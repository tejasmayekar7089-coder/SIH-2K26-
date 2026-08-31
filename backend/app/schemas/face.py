from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

class FaceMatchStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    SKIPPED_NO_PORTRAIT = "SKIPPED_NO_PORTRAIT"
    SKIPPED_NO_LIVE_IMAGE = "SKIPPED_NO_LIVE_IMAGE"
    FAILED_DETECTION = "FAILED_DETECTION"

class FaceResult(BaseModel):
    is_conditional_executed: bool = True
    match_status: FaceMatchStatus
    similarity_score: float = Field(default=0.0, ge=0.0, le=1.0, description="1:1 Cosine Similarity")
    match_threshold: float = 0.65
    
    # Biometric quality
    document_face_detected: bool = False
    document_face_quality: float = 0.0
    live_face_detected: bool = False
    live_face_quality: float = 0.0
    
    notes: str = "Strict 1:1 Face Verification only. Strictly no 1:N mass identification."
