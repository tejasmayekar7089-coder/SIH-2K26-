import pytest
from app.schemas.document import DocumentCategory, QualityResult
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.mrz import MRZResult, MRZFormat, ConsistencyStatus, CheckDigitVerification, FieldConsistencyCheck
from app.schemas.metadata import MetadataResult, MetadataClassification
from app.schemas.validation import RuleStatus, ValidationResult, RuleEvaluation, ValidationCategory
from app.modules.validation.service import ValidationService
from app.modules.validation.registry import DocumentValidatorRegistry, BaseValidationRule

def test_aadhaar_validation_pass():
    service = ValidationService()
    extraction = ExtractionResult(
        document_category=DocumentCategory.AADHAAR,
        document_number=ExtractedField(field_name="aadhaar_number", value="2345 6789 0122", confidence=0.98),
        full_name=ExtractedField(field_name="name", value="Arjun Sharma", confidence=0.96),
        date_of_birth=ExtractedField(field_name="date_of_birth", value="1992-05-14", confidence=0.95),
        gender=ExtractedField(field_name="gender", value="MALE", confidence=0.99),
        ocr_confidence_mean=0.95
    )
    quality = QualityResult(quality_score=0.85, is_blurred=False)

    res = service.perform_deterministic_validation(extraction=extraction, quality=quality)

    assert res.overall_status == RuleStatus.PASS
    assert res.failure_count == 0
    assert res.inconsistency_count == 0
    verhoeff_eval = next(e for e in res.evaluations if e.rule_id == "RULE_AADHAAR_VERHOEFF")
    assert verhoeff_eval.status == RuleStatus.PASS

def test_aadhaar_validation_verhoeff_fail():
    service = ValidationService()
    # Invalid Verhoeff checksum
    extraction = ExtractionResult(
        document_category=DocumentCategory.AADHAAR,
        document_number=ExtractedField(field_name="aadhaar_number", value="2345 6789 0120", confidence=0.98),
        full_name=ExtractedField(field_name="name", value="Arjun Sharma", confidence=0.96),
        date_of_birth=ExtractedField(field_name="date_of_birth", value="1992-05-14", confidence=0.95),
        gender=ExtractedField(field_name="gender", value="MALE", confidence=0.99),
        ocr_confidence_mean=0.95
    )
    quality = QualityResult(quality_score=0.85, is_blurred=False)

    res = service.perform_deterministic_validation(extraction=extraction, quality=quality)

    assert res.overall_status == RuleStatus.FAIL
    assert res.failure_count >= 1
    verhoeff_eval = next(e for e in res.evaluations if e.rule_id == "RULE_AADHAAR_VERHOEFF")
    assert verhoeff_eval.status == RuleStatus.FAIL
    assert verhoeff_eval.reason_code == "INVALID_AADHAAR_VERHOEFF"

def test_dl_validation_inverted_dates_fail():
    service = ValidationService()
    # Inverted dates: issue date (2030) > expiry date (2020)
    extraction = ExtractionResult(
        document_category=DocumentCategory.DRIVING_LICENSE,
        document_number=ExtractedField(field_name="driving_licence_number", value="MH-12-20180012345", confidence=0.98),
        full_name=ExtractedField(field_name="name", value="Priya Sharma", confidence=0.96),
        date_of_birth=ExtractedField(field_name="date_of_birth", value="1995-10-20", confidence=0.95),
        issue_date=ExtractedField(field_name="date_of_issue", value="2030-01-15", confidence=0.95),
        expiry_date=ExtractedField(field_name="validity_expiry_date", value="2020-01-14", confidence=0.95),
        ocr_confidence_mean=0.92
    )

    res = service.perform_deterministic_validation(extraction=extraction)

    assert res.overall_status == RuleStatus.FAIL
    date_eval = next(e for e in res.evaluations if e.rule_id == "RULE_DL_CHRONOLOGY")
    assert date_eval.status == RuleStatus.FAIL
    assert date_eval.reason_code == "INVERTED_DATE_SEQUENCE"
    assert date_eval.severity == "HIGH"

def test_passport_validation_mrz_mismatch_inconsistent():
    service = ValidationService()
    extraction = ExtractionResult(
        document_category=DocumentCategory.PASSPORT,
        document_number=ExtractedField(field_name="passport_number", value="X9999999", confidence=0.95),
        full_name=ExtractedField(field_name="name", value="Arjun Sharma", confidence=0.95),
        date_of_birth=ExtractedField(field_name="date_of_birth", value="1992-05-14", confidence=0.95),
        ocr_confidence_mean=0.95
    )
    mrz = MRZResult(
        is_present=True,
        mrz_format=MRZFormat.TD3,
        document_number="P8923412",
        all_check_digits_valid=True,
        overall_consistency_status=ConsistencyStatus.MISMATCH,
        consistency_checks=[
            FieldConsistencyCheck(
                field_name="Passport Number",
                printed_viz_value="X9999999",
                mrz_value="P8923412",
                status=ConsistencyStatus.MISMATCH
            )
        ]
    )

    res = service.perform_deterministic_validation(extraction=extraction, mrz=mrz)

    assert res.overall_status == RuleStatus.INCONSISTENT
    mrz_eval = next(e for e in res.evaluations if e.rule_id == "RULE_PASSPORT_VIZ_MRZ_CONSISTENCY")
    assert mrz_eval.status == RuleStatus.INCONSISTENT
    assert mrz_eval.reason_code == "VIZ_MRZ_MISMATCH"

def test_engine_determinism_identical_outputs():
    """Validates that running the engine 20 times on identical inputs produces 100% identical outputs."""
    service = ValidationService()
    extraction = ExtractionResult(
        document_category=DocumentCategory.AADHAAR,
        document_number=ExtractedField(field_name="aadhaar_number", value="2345 6789 0122", confidence=0.98),
        full_name=ExtractedField(field_name="name", value="Arjun Sharma", confidence=0.96),
        date_of_birth=ExtractedField(field_name="date_of_birth", value="1992-05-14", confidence=0.95),
        gender=ExtractedField(field_name="gender", value="MALE", confidence=0.99),
        ocr_confidence_mean=0.95
    )
    quality = QualityResult(quality_score=0.85, is_blurred=False)

    baseline_res = service.perform_deterministic_validation(extraction=extraction, quality=quality)

    for _ in range(20):
        iter_res = service.perform_deterministic_validation(extraction=extraction, quality=quality)
        assert iter_res.overall_status == baseline_res.overall_status
        assert iter_res.inconsistency_count == baseline_res.inconsistency_count
        assert iter_res.failure_count == baseline_res.failure_count
        assert len(iter_res.evaluations) == len(baseline_res.evaluations)
        for e1, e2 in zip(baseline_res.evaluations, iter_res.evaluations):
            assert e1.rule_id == e2.rule_id
            assert e1.status == e2.status
            assert e1.reason_code == e2.reason_code

class CustomTestRule(BaseValidationRule):
    rule_id = "RULE_CUSTOM_01"
    rule_name = "Custom Dynamic Rule"
    category = ValidationCategory.INTERNAL_CONSISTENCY

    def evaluate(self, extraction, mrz=None, metadata=None, quality=None):
        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Custom rule evaluation",
            status=RuleStatus.PASS,
            reason_code="CUSTOM_RULE_PASS",
            reason="Custom dynamic rule evaluated cleanly."
        )

def test_rule_registry_dynamic_extension():
    registry = DocumentValidatorRegistry()
    registry.register_rule(DocumentCategory.UNKNOWN, CustomTestRule())

    service = ValidationService(registry=registry)
    extraction = ExtractionResult(document_category=DocumentCategory.UNKNOWN)

    res = service.perform_deterministic_validation(extraction=extraction)

    assert len(res.evaluations) == 1
    assert res.evaluations[0].rule_id == "RULE_CUSTOM_01"
    assert res.evaluations[0].reason_code == "CUSTOM_RULE_PASS"
