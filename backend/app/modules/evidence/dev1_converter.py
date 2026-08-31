from typing import List, Optional, Dict, Any
from app.schemas.common import EvidenceItem, SeverityLevel
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult, MetadataClassification
from app.schemas.validation import ValidationResult, RuleStatus
from app.core.logging import get_logger

logger = get_logger("dev1_evidence_converter")

class Developer1EvidenceConverter:
    """Standardizes and converts analytical results from Developer 1 modules into common EvidenceItem objects."""

    @classmethod
    def convert_quality(cls, quality: Optional[QualityResult]) -> List[EvidenceItem]:
        """Converts Module 2 QualityResult to EvidenceItem list."""
        if not quality:
            return []

        sev = SeverityLevel.LOW if quality.is_acceptable else SeverityLevel.MEDIUM
        item = EvidenceItem(
            source_module="ACQUISITION_QUALITY",
            data={
                "quality_score": quality.quality_score,
                "blur_score": quality.blur_score,
                "is_blurred": quality.is_blurred,
                "glare_score": quality.glare_score,
                "has_glare": quality.has_glare,
                "resolution_dpi": quality.resolution_dpi
            },
            confidence=0.95,
            strength=0.70,
            severity=sev,
            provenance="OpenCV Laplacian/Glare/Dimension Metric Analyzer v1.0",
            reason_code="IMAGE_BLUR_DETECTED" if quality.is_blurred else ("IMAGE_GLARE_DETECTED" if quality.has_glare else "QUALITY_ACCEPTABLE")
        )
        return [item]

    @classmethod
    def convert_extraction(cls, extraction: Optional[ExtractionResult]) -> List[EvidenceItem]:
        """Converts Module 3 ExtractionResult fields into field-level EvidenceItem objects."""
        if not extraction:
            return []

        items: List[EvidenceItem] = []
        field_mapping: Dict[str, Optional[ExtractedField]] = {
            "document_number": extraction.document_number,
            "full_name": extraction.full_name,
            "date_of_birth": extraction.date_of_birth,
            "gender": extraction.gender,
            "nationality": extraction.nationality,
            "issue_date": extraction.issue_date,
            "expiry_date": extraction.expiry_date,
            "address": extraction.address
        }

        # Include additional extracted fields
        if extraction.additional_fields:
            for k, v in extraction.additional_fields.items():
                if k not in field_mapping and isinstance(v, ExtractedField):
                    field_mapping[k] = v

        for field_key, field_obj in field_mapping.items():
            if field_obj and field_obj.value:
                # Map field severity string to SeverityLevel enum
                sev_enum = cls._parse_severity(getattr(field_obj, "severity", "LOW"))
                bbox_coords = field_obj.bbox if hasattr(field_obj, "bbox") else (
                    [field_obj.bounding_box.x, field_obj.bounding_box.y,
                     field_obj.bounding_box.x + field_obj.bounding_box.width,
                     field_obj.bounding_box.y + field_obj.bounding_box.height] if field_obj.bounding_box else None
                )

                item = EvidenceItem(
                    source_module="DOCUMENT_INTELLIGENCE",
                    data={
                        "field": field_obj.field_name or field_key,
                        "value": field_obj.value,
                        "document_category": extraction.document_category.value
                    },
                    confidence=field_obj.confidence,
                    strength=0.90,
                    severity=sev_enum,
                    provenance=getattr(field_obj, "provenance", f"ocr:{extraction.document_category.value.lower()}"),
                    bbox=bbox_coords,
                    reason_code="FIELD_EXTRACTED"
                )
                items.append(item)

        return items

    @classmethod
    def convert_mrz(cls, mrz: Optional[MRZResult]) -> List[EvidenceItem]:
        """Converts Module 4A MRZResult into EvidenceItem objects."""
        if not mrz or not mrz.is_present:
            return []

        items: List[EvidenceItem] = []

        # MRZ Overall Integrity Item
        mrz_sev = SeverityLevel.LOW if mrz.all_check_digits_valid else SeverityLevel.HIGH
        items.append(EvidenceItem(
            source_module="MRZ_PROCESSING",
            data={
                "mrz_format": mrz.mrz_format.value,
                "document_number": mrz.document_number,
                "date_of_birth": mrz.date_of_birth,
                "expiry_date": mrz.expiry_date,
                "all_check_digits_valid": mrz.all_check_digits_valid,
                "overall_consistency_status": mrz.overall_consistency_status.value
            },
            confidence=0.98,
            strength=0.95,
            severity=mrz_sev,
            provenance="ICAO 9303 TD3 MRZ Engine v1.0",
            reason_code="MRZ_CHECKSUMS_VALID" if mrz.all_check_digits_valid else "MRZ_CHECKSUMS_FAILED",
            bbox=[mrz.bounding_box.x, mrz.bounding_box.y, mrz.bounding_box.x + mrz.bounding_box.width, mrz.bounding_box.y + mrz.bounding_box.height] if mrz.bounding_box else None
        ))

        # Field Consistency Evidence Items
        if mrz.consistency_checks:
            for check in mrz.consistency_checks:
                check_sev = SeverityLevel.HIGH if check.status.value == "MISMATCH" else SeverityLevel.LOW
                items.append(EvidenceItem(
                    source_module="MRZ_PROCESSING",
                    data={
                        "field": f"MRZ_CONSISTENCY_{check.field_name.upper().replace(' ', '_')}",
                        "printed_viz_value": check.printed_viz_value,
                        "mrz_value": check.mrz_value,
                        "status": check.status.value,
                        "notes": check.notes
                    },
                    confidence=0.95,
                    strength=0.90,
                    severity=check_sev,
                    provenance="MRZ-VIZ Consistency Cross-Checker v1.0",
                    reason_code=f"VIZ_MRZ_{check.status.value}"
                ))

        return items

    @classmethod
    def convert_metadata(cls, metadata: Optional[MetadataResult]) -> List[EvidenceItem]:
        """Converts Module 4B MetadataResult to EvidenceItem list."""
        if not metadata:
            return []

        if metadata.metadata_classification == MetadataClassification.SUSPICIOUS_METADATA:
            meta_sev = SeverityLevel.MEDIUM
            reason_code = "SUSPICIOUS_METADATA_SOFTWARE"
        elif metadata.metadata_classification == MetadataClassification.SUPPORTING:
            meta_sev = SeverityLevel.LOW
            reason_code = "CAMERA_EXIF_PRESENT"
        else:
            meta_sev = SeverityLevel.LOW
            reason_code = "METADATA_NOT_AVAILABLE"

        item = EvidenceItem(
            source_module="METADATA_ANALYSIS",
            data={
                "file_type": metadata.file_type,
                "mime_type": metadata.mime_type,
                "file_size_bytes": metadata.file_size_bytes,
                "has_exif": metadata.has_exif,
                "software_signature": metadata.software_signature,
                "metadata_classification": metadata.metadata_classification.value,
                "has_editing_signature": metadata.has_editing_signature
            },
            confidence=0.90,
            strength=0.60,
            severity=meta_sev,
            provenance="Pillow/ExifRead Digital Header Inspector v1.0",
            reason_code=reason_code
        )
        return [item]

    @classmethod
    def convert_validation(cls, validation: Optional[ValidationResult]) -> List[EvidenceItem]:
        """Converts Module 5 ValidationResult evaluations into EvidenceItem objects."""
        if not validation or not validation.evaluations:
            return []

        items: List[EvidenceItem] = []
        for eval_res in validation.evaluations:
            eval_sev = cls._parse_severity(eval_res.severity)
            item = EvidenceItem(
                source_module="DETERMINISTIC_VALIDATION",
                data={
                    "rule_id": eval_res.rule_id,
                    "rule_name": eval_res.rule_name,
                    "category": eval_res.category.value,
                    "status": eval_res.status.value,
                    "field_affected": eval_res.field_affected,
                    "expected_value": eval_res.expected_value,
                    "actual_value": eval_res.actual_value,
                    "reason": eval_res.reason
                },
                confidence=1.0,  # Deterministic rule evaluations carry 1.0 confidence
                strength=0.95,
                severity=eval_sev,
                provenance=f"RuleEngine:{eval_res.rule_id}",
                reason_code=eval_res.reason_code
            )
            items.append(item)

        return items

    @classmethod
    def aggregate_dev1_evidence(
        cls,
        quality: Optional[QualityResult] = None,
        extraction: Optional[ExtractionResult] = None,
        mrz: Optional[MRZResult] = None,
        metadata: Optional[MetadataResult] = None,
        validation: Optional[ValidationResult] = None
    ) -> List[EvidenceItem]:
        """Aggregates all analytical outputs from Developer 1 into a standardized list of EvidenceItems."""
        all_items: List[EvidenceItem] = []
        all_items.extend(cls.convert_quality(quality))
        all_items.extend(cls.convert_extraction(extraction))
        all_items.extend(cls.convert_mrz(mrz))
        all_items.extend(cls.convert_metadata(metadata))
        all_items.extend(cls.convert_validation(validation))
        return all_items

    @staticmethod
    def _parse_severity(sev_input: Any) -> SeverityLevel:
        """Helper to parse severity string or enum safely."""
        if isinstance(sev_input, SeverityLevel):
            return sev_input
        sev_str = str(sev_input).upper()
        if "HIGH" in sev_str:
            return SeverityLevel.HIGH
        elif "MEDIUM" in sev_str:
            return SeverityLevel.MEDIUM
        return SeverityLevel.LOW
