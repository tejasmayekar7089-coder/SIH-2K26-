from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field
from app.schemas.common import EvidenceItem
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import ValidationResult
from app.schemas.tampering import TamperResult
from app.schemas.field_mapping import FieldMappingResult
from app.schemas.face import FaceResult
from app.schemas.database import DatabaseResult

class EvidenceBundle(BaseModel):
    screening_id: str
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Normalized items
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    
    # Typed module payloads
    quality_result: Optional[QualityResult] = None
    extraction_result: Optional[ExtractionResult] = None
    mrz_result: Optional[MRZResult] = None
    metadata_result: Optional[MetadataResult] = None
    validation_result: Optional[ValidationResult] = None
    tamper_result: Optional[TamperResult] = None
    field_mapping_result: Optional[FieldMappingResult] = None
    face_result: Optional[FaceResult] = None
    database_result: Optional[DatabaseResult] = None
    
    principle: str = "No single model has authority."
