from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class RuleStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONSISTENT = "INCONSISTENT"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    SKIPPED = "SKIPPED"

class ValidationCategory(str, Enum):
    FIELD_PRESENCE = "FIELD_PRESENCE"
    FIELD_FORMAT = "FIELD_FORMAT"
    DATE_VALIDITY = "DATE_VALIDITY"
    DATE_ORDERING = "DATE_ORDERING"
    INTERNAL_CONSISTENCY = "INTERNAL_CONSISTENCY"
    MRZ_CHECK_DIGITS = "MRZ_CHECK_DIGITS"
    OCR_MRZ_CONSISTENCY = "OCR_MRZ_CONSISTENCY"
    OCR_CONFIDENCE = "OCR_CONFIDENCE"
    DOCUMENT_QUALITY = "DOCUMENT_QUALITY"

class RuleEvaluation(BaseModel):
    rule_id: str
    rule_name: str
    category: ValidationCategory
    description: str
    status: RuleStatus
    severity: str = "LOW"  # LOW, MEDIUM, HIGH
    reason_code: str = "CHECK_PASSED"
    field_affected: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    reason: str

class ValidationResult(BaseModel):
    overall_status: RuleStatus = RuleStatus.PASS
    validation_mode: str = "STRICT"  # "STRICT" or "TEST_FIXTURE"
    is_synthetic_fixture: bool = False
    fixture_id: Optional[str] = None
    fixture_description: Optional[str] = None
    raw_validation_status: Optional[str] = None
    format_valid: bool = True
    date_logic_valid: bool = True
    mrz_viz_consistent: bool = True
    evaluations: List[RuleEvaluation] = Field(default_factory=list)
    inconsistency_count: int = 0
    failure_count: int = 0
    summary_notes: str = "Deterministic validation checks internal syntax, format, and cross-field consistency ONLY. Validation status does NOT constitute official government verification of document authenticity."
