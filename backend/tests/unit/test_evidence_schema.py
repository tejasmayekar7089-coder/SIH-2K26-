import pytest
from app.schemas.common import EvidenceItem, SeverityLevel
from app.schemas.document import DocumentCategory, QualityResult
from app.schemas.extraction import ExtractionResult, ExtractedField, BoundingBox
from app.schemas.mrz import MRZResult, MRZFormat, ConsistencyStatus, FieldConsistencyCheck
from app.schemas.metadata import MetadataResult, MetadataClassification
from app.schemas.validation import ValidationResult, RuleStatus, RuleEvaluation, ValidationCategory
from app.schemas.evidence import EvidenceBundle
from app.modules.evidence.dev1_converter import Developer1EvidenceConverter
from app.modules.evidence.builder import EvidenceBuilderService

def test_evidence_item_pydantic_validation_and_field_dict():
    item = EvidenceItem(
        source_module="DOCUMENT_INTELLIGENCE",
        data={"field": "date_of_birth", "value": "1992-05-14"},
        confidence=0.95,
        strength=0.90,
        severity=SeverityLevel.LOW,
        provenance="ocr:paddleocr",
        bbox=[100, 120, 300, 145],
        reason_code="FIELD_EXTRACTED"
    )

    field_dict = item.to_field_evidence_dict()

    assert field_dict["field"] == "date_of_birth"
    assert field_dict["data"] == "1992-05-14"
    assert field_dict["confidence"] == 0.95
    assert field_dict["strength"] == 0.90
    assert field_dict["severity"] == "LOW"
    assert field_dict["provenance"] == "ocr:paddleocr"
    assert field_dict["bbox"] == [100, 120, 300, 145]
    assert field_dict["reason_code"] == "FIELD_EXTRACTED"

def test_convert_quality_to_evidence():
    quality = QualityResult(quality_score=0.88, is_blurred=False, glare_score=0.01)
    items = Developer1EvidenceConverter.convert_quality(quality)

    assert len(items) == 1
    assert items[0].source_module == "ACQUISITION_QUALITY"
    assert items[0].confidence == 0.95
    assert items[0].severity == SeverityLevel.LOW
    assert items[0].reason_code == "QUALITY_ACCEPTABLE"

def test_convert_extraction_to_field_evidence():
    extraction = ExtractionResult(
        document_category=DocumentCategory.AADHAAR,
        document_number=ExtractedField(
            field_name="aadhaar_number",
            value="2345 6789 0122",
            confidence=0.98,
            bbox=[50, 100, 450, 130],
            provenance="ocr:aadhaar_extractor"
        ),
        date_of_birth=ExtractedField(
            field_name="date_of_birth",
            value="1992-05-14",
            confidence=0.95,
            bbox=[50, 140, 250, 170],
            provenance="ocr:aadhaar_extractor"
        )
    )

    items = Developer1EvidenceConverter.convert_extraction(extraction)

    assert len(items) == 2
    num_item = next(i for i in items if i.data["field"] == "aadhaar_number")
    assert num_item.data["value"] == "2345 6789 0122"
    assert num_item.confidence == 0.98
    assert num_item.bbox == [50, 100, 450, 130]

    dob_item = next(i for i in items if i.data["field"] == "date_of_birth")
    field_dict = dob_item.to_field_evidence_dict()
    assert field_dict["field"] == "date_of_birth"
    assert field_dict["data"] == "1992-05-14"

def test_convert_mrz_to_evidence():
    mrz = MRZResult(
        is_present=True,
        mrz_format=MRZFormat.TD3,
        document_number="P8923412",
        all_check_digits_valid=True,
        overall_consistency_status=ConsistencyStatus.MATCH,
        consistency_checks=[
            FieldConsistencyCheck(
                field_name="Passport Number",
                printed_viz_value="P8923412",
                mrz_value="P8923412",
                status=ConsistencyStatus.MATCH
            )
        ]
    )

    items = Developer1EvidenceConverter.convert_mrz(mrz)

    assert len(items) == 2
    mrz_item = items[0]
    assert mrz_item.source_module == "MRZ_PROCESSING"
    assert mrz_item.severity == SeverityLevel.LOW
    assert mrz_item.reason_code == "MRZ_CHECKSUMS_VALID"

def test_convert_metadata_to_evidence():
    metadata = MetadataResult(
        file_type="JPG",
        mime_type="image/jpeg",
        file_size_bytes=120000,
        has_exif=True,
        software_signature="Adobe Photoshop CC 2024",
        metadata_classification=MetadataClassification.SUSPICIOUS_METADATA,
        has_editing_signature=True
    )

    items = Developer1EvidenceConverter.convert_metadata(metadata)

    assert len(items) == 1
    assert items[0].source_module == "METADATA_ANALYSIS"
    assert items[0].severity == SeverityLevel.MEDIUM
    assert items[0].reason_code == "SUSPICIOUS_METADATA_SOFTWARE"

def test_convert_validation_to_evidence():
    validation = ValidationResult(
        overall_status=RuleStatus.FAIL,
        evaluations=[
            RuleEvaluation(
                rule_id="RULE_AADHAAR_VERHOEFF",
                rule_name="Aadhaar Verhoeff Checksum",
                category=ValidationCategory.FIELD_FORMAT,
                description="Verhoeff Checksum Check",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="INVALID_AADHAAR_VERHOEFF",
                reason="Verhoeff checksum failed."
            )
        ]
    )

    items = Developer1EvidenceConverter.convert_validation(validation)

    assert len(items) == 1
    assert items[0].source_module == "DETERMINISTIC_VALIDATION"
    assert items[0].confidence == 1.0
    assert items[0].severity == SeverityLevel.HIGH
    assert items[0].reason_code == "INVALID_AADHAAR_VERHOEFF"

def test_aggregate_dev1_evidence_and_bundle_integration():
    quality = QualityResult(quality_score=0.90, is_blurred=False)
    extraction = ExtractionResult(
        document_category=DocumentCategory.PASSPORT,
        document_number=ExtractedField(field_name="passport_number", value="P1234567", confidence=0.96)
    )
    metadata = MetadataResult(
        file_type="JPG",
        file_size_bytes=100000,
        metadata_classification=MetadataClassification.SUPPORTING
    )
    validation = ValidationResult(overall_status=RuleStatus.PASS)

    builder = EvidenceBuilderService()
    bundle = builder.build_evidence_bundle(
        screening_id="SCR-DEV1-001",
        quality=quality,
        extraction=extraction,
        mrz=None,
        metadata=metadata,
        validation=validation
    )

    assert isinstance(bundle, EvidenceBundle)
    assert bundle.screening_id == "SCR-DEV1-001"
    assert len(bundle.evidence_items) >= 3
    source_modules = [item.source_module for item in bundle.evidence_items]
    assert "ACQUISITION_QUALITY" in source_modules
    assert "DOCUMENT_INTELLIGENCE" in source_modules
    assert "METADATA_ANALYSIS" in source_modules
