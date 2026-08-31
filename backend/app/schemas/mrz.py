from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox

class MRZFormat(str, Enum):
    TD1 = "TD1"  # ID Cards (3 lines x 30 chars)
    TD2 = "TD2"  # Visas / ID (2 lines x 36 chars)
    TD3 = "TD3"  # Passports (2 lines x 44 chars)
    NONE = "NONE"

class ConsistencyStatus(str, Enum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"

class CheckDigitVerification(BaseModel):
    field_name: str
    extracted_value: str
    expected_check_digit: str
    computed_check_digit: str
    is_valid: bool
    source: str = "icao_9303_engine"
    provenance: str = "icao9303_weighted_checksum"

class FieldConsistencyCheck(BaseModel):
    field_name: str
    printed_viz_value: Optional[str] = None
    mrz_value: Optional[str] = None
    status: ConsistencyStatus = ConsistencyStatus.NOT_AVAILABLE
    notes: str = ""

class MRZResult(BaseModel):
    is_present: bool = False
    mrz_format: MRZFormat = MRZFormat.NONE
    raw_mrz_lines: List[str] = Field(default_factory=list)
    raw_mrz_text: str = ""
    bounding_box: Optional[BoundingBox] = None
    
    # Extracted from MRZ
    document_type: Optional[str] = None
    country_code: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    document_number: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYMMDD or YYYY-MM-DD
    gender: Optional[str] = None
    expiry_date: Optional[str] = None    # YYMMDD or YYYY-MM-DD
    optional_data: Optional[str] = None
    
    # Validation results
    check_digits: List[CheckDigitVerification] = Field(default_factory=list)
    all_check_digits_valid: bool = True
    parsing_errors: List[str] = Field(default_factory=list)
    
    # Consistency verification results (Printed VIZ vs MRZ)
    consistency_checks: List[FieldConsistencyCheck] = Field(default_factory=list)
    overall_consistency_status: ConsistencyStatus = ConsistencyStatus.NOT_AVAILABLE

    source: str = "td3_mrz_processor"
    provenance: str = "mrz_detector_parser_validator"
    disclaimer: str = "Check-digit validation proves internal MRZ data integrity ONLY; it does NOT constitute government database verification."
