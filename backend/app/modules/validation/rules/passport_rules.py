from typing import Optional
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult, ConsistencyStatus
from app.schemas.metadata import MetadataResult
from app.schemas.validation import RuleEvaluation, RuleStatus, ValidationCategory
from app.modules.validation.registry import BaseValidationRule

class PassportPresenceRule(BaseValidationRule):
    rule_id = "RULE_PASSPORT_PRESENCE"
    rule_name = "Passport Field Presence"
    category = ValidationCategory.FIELD_PRESENCE

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        missing = []
        if not extraction.document_number:
            missing.append("passport_number")
        if not extraction.full_name:
            missing.append("name")
        if not extraction.date_of_birth:
            missing.append("date_of_birth")

        if missing:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Assert presence of required Passport VIZ fields",
                status=RuleStatus.INCONSISTENT,
                severity="MEDIUM",
                reason_code="MISSING_REQUIRED_FIELD",
                field_affected=", ".join(missing),
                reason=f"Missing {len(missing)} required Passport field(s): {', '.join(missing)}"
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Assert presence of required Passport VIZ fields",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="All core Passport fields are present."
        )

class PassportMRZCheckDigitRule(BaseValidationRule):
    rule_id = "RULE_PASSPORT_MRZ_CHECKSUMS"
    rule_name = "ICAO 9303 MRZ Check Digit Integrity"
    category = ValidationCategory.MRZ_CHECK_DIGITS

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not mrz or not mrz.is_present:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verify ICAO 9303 mathematical MRZ check digits",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="MRZ_NOT_PRESENT",
                reason="MRZ not present or readable on passport page."
            )

        if not mrz.all_check_digits_valid:
            failed_cd = [cd.field_name for cd in mrz.check_digits if not cd.is_valid]
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verify ICAO 9303 mathematical MRZ check digits",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="MRZ_CHECKSUM_FAILURE",
                field_affected=", ".join(failed_cd),
                expected_value="All Check Digits Valid",
                actual_value=f"Failed: {', '.join(failed_cd)}",
                reason=f"MRZ check digit validation failed for: {', '.join(failed_cd)}."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Verify ICAO 9303 mathematical MRZ check digits",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="All ICAO 9303 MRZ check digits are mathematically valid."
        )

class PassportOCZMRZConsistencyRule(BaseValidationRule):
    rule_id = "RULE_PASSPORT_VIZ_MRZ_CONSISTENCY"
    rule_name = "Printed VIZ vs MRZ Cross-Field Consistency"
    category = ValidationCategory.OCR_MRZ_CONSISTENCY

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not mrz or not mrz.is_present or not mrz.consistency_checks:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Cross-check printed VIZ fields against parsed MRZ fields",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="MRZ_CONSISTENCY_NOT_AVAILABLE",
                reason="MRZ consistency checks unavailable."
            )

        if mrz.overall_consistency_status == ConsistencyStatus.MISMATCH:
            mismatches = [c for c in mrz.consistency_checks if c.status == ConsistencyStatus.MISMATCH]
            field_names = [m.field_name for m in mismatches]
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Cross-check printed VIZ fields against parsed MRZ fields",
                status=RuleStatus.INCONSISTENT,
                severity="HIGH",
                reason_code="VIZ_MRZ_MISMATCH",
                field_affected=", ".join(field_names),
                reason=f"Discrepancy detected between printed VIZ and MRZ for: {', '.join(field_names)}."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Cross-check printed VIZ fields against parsed MRZ fields",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="Printed VIZ fields match parsed MRZ fields."
        )
