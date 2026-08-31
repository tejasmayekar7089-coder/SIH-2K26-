from dataclasses import dataclass
from typing import Optional

@dataclass
class ScreeningDBRecord:
    screening_id: str
    timestamp_utc: str
    document_id: str
    file_name: str
    sha256_checksum: str
    risk_level: str
    risk_score: int
    top_reasons: str
    officer_action: str
    officer_notes: Optional[str]
    processing_time_ms: float
    evidence_bundle_json: str

@dataclass
class MockRegistryRecord:
    document_number: str
    country_code: str
    holder_name: str
    status: str
    issue_date: str
    expiry_date: str
    remarks: str
