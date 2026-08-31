from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.schemas.common import EvidenceItem, SeverityLevel
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import ValidationResult, RuleStatus
from app.schemas.tampering import TamperResult
from app.schemas.field_mapping import FieldMappingResult
from app.schemas.face import FaceResult, FaceMatchStatus
from app.schemas.database import DatabaseResult, RegistryStatus
from app.schemas.evidence import EvidenceBundle
from app.modules.evidence.dev1_converter import Developer1EvidenceConverter
from app.core.logging import get_logger

logger = get_logger("evidence_builder")

class EvidenceBuilderService:
    def __init__(self):
        pass

    def build_evidence_bundle(
        self,
        screening_id: str,
        quality: Optional[QualityResult] = None,
        extraction: Optional[ExtractionResult] = None,
        mrz: Optional[MRZResult] = None,
        metadata: Optional[MetadataResult] = None,
        validation: Optional[ValidationResult] = None,
        tampering: Optional[TamperResult] = None,
        field_mapping: Optional[FieldMappingResult] = None,
        face: Optional[FaceResult] = None,
        database: Optional[DatabaseResult] = None
    ) -> EvidenceBundle:
        """Module 10: Evidence Builder — Schema Normalization & Aggregation."""
        logger.info(f"Building normalized evidence bundle for: {screening_id}")
        
        # 1. Aggregate Developer 1 evidence items
        items: List[EvidenceItem] = Developer1EvidenceConverter.aggregate_dev1_evidence(
            quality=quality,
            extraction=extraction,
            mrz=mrz,
            metadata=metadata,
            validation=validation
        )

        # 2. Downstream Module Evidence Aggregation
        if tampering:
            items.append(EvidenceItem(
                source_module="TAMPERING_AI",
                data={"tamper_score": tampering.tamper_score, "model_used": tampering.model_used.value},
                confidence=0.88,
                strength=0.90,
                severity=SeverityLevel.HIGH if tampering.is_tampered else SeverityLevel.LOW,
                provenance=f"Model: {tampering.model_used.value}",
                reason_code="IMAGE_TAMPERING_DETECTED" if tampering.is_tampered else "NO_TAMPERING_DETECTED"
            ))

        if field_mapping and field_mapping.has_tampered_fields:
            items.append(EvidenceItem(
                source_module="FIELD_EVIDENCE_MAPPING",
                data={"highest_field": field_mapping.highest_risk_field, "severity": field_mapping.highest_severity.value},
                confidence=0.92,
                strength=0.95,
                severity=field_mapping.highest_severity,
                provenance="Spatial IoU Mask-BBox Intersector v1.0",
                reason_code="FIELD_TAMPERING_OVERLAP"
            ))

        if face and face.is_conditional_executed:
            items.append(EvidenceItem(
                source_module="FACE_VERIFICATION",
                data={"status": face.match_status.value, "similarity": face.similarity_score},
                confidence=0.94,
                strength=0.90,
                severity=SeverityLevel.LOW if face.match_status == FaceMatchStatus.MATCH else SeverityLevel.HIGH,
                provenance="InsightFace ArcFace 1:1 Cosine Model",
                reason_code=f"FACE_VERIFICATION_{face.match_status.value}"
            ))

        if database:
            items.append(EvidenceItem(
                source_module="MOCK_DATABASE_INTEL",
                data={"status": database.status.value, "remarks": database.remarks},
                confidence=1.0,
                strength=1.0,
                severity=SeverityLevel.HIGH if database.status in [RegistryStatus.STOLEN, RegistryStatus.REVOKED, RegistryStatus.WATCHLIST] else SeverityLevel.LOW,
                provenance="Simulated Watchlist SQLite Registry",
                reason_code=f"DATABASE_{database.status.value}"
            ))

        return EvidenceBundle(
            screening_id=screening_id,
            evidence_items=items,
            quality_result=quality,
            extraction_result=extraction,
            mrz_result=mrz,
            metadata_result=metadata,
            validation_result=validation,
            tamper_result=tampering,
            field_mapping_result=field_mapping,
            face_result=face,
            database_result=database
        )
