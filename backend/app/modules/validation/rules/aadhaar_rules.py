import re
from datetime import datetime
from typing import Optional
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import RuleEvaluation, RuleStatus, ValidationCategory
from app.modules.validation.registry import BaseValidationRule
from app.modules.document_intelligence.extractors.aadhaar import verhoeff_validate

class AadhaarPresenceRule(BaseValidationRule):
    rule_id = "RULE_AADHAAR_PRESENCE"
    rule_name = "Aadhaar Required Field Presence"
    category = ValidationCategory.FIELD_PRESENCE

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        required = ["aadhaar_number", "name", "date_of_birth", "gender"]
        missing = []

        if not extraction.document_number:
            missing.append("aadhaar_number")
        if not extraction.full_name:
            missing.append("name")
        if not extraction.date_of_birth:
            missing.append("date_of_birth")
        if not extraction.gender:
            missing.append("gender")

        if missing:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Assert presence of required Aadhaar fields",
                status=RuleStatus.INCONSISTENT,
                severity="MEDIUM",
                reason_code="MISSING_REQUIRED_FIELD",
                field_affected=", ".join(missing),
                reason=f"Missing {len(missing)} required Aadhaar field(s): {', '.join(missing)}"
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Assert presence of required Aadhaar fields",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="All core required Aadhaar fields are present."
        )

class AadhaarVerhoeffRule(BaseValidationRule):
    rule_id = "RULE_AADHAAR_VERHOEFF"
    rule_name = "Aadhaar 12-Digit Verhoeff Checksum"
    category = ValidationCategory.FIELD_FORMAT

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not extraction.document_number or not extraction.document_number.value:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verhoeff 12th-digit mathematical checksum verification",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="AADHAAR_NUM_MISSING",
                reason="Aadhaar number missing."
            )

        raw_digits = re.sub(r'\D', '', extraction.document_number.value)
        if len(raw_digits) != 12:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verhoeff 12th-digit mathematical checksum verification",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="INVALID_AADHAAR_LENGTH",
                field_affected="aadhaar_number",
                actual_value=f"{len(raw_digits)} digits",
                expected_value="12 digits",
                reason=f"Aadhaar number must contain exactly 12 numeric digits (found {len(raw_digits)})."
            )

        is_valid = verhoeff_validate(raw_digits)
        if not is_valid:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verhoeff 12th-digit mathematical checksum verification",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="INVALID_AADHAAR_VERHOEFF",
                field_affected="aadhaar_number",
                actual_value="Invalid Checksum",
                expected_value="Valid Verhoeff Checksum",
                reason="Aadhaar number failed Verhoeff mathematical 12th-digit checksum validation."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Verhoeff 12th-digit mathematical checksum verification",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="Aadhaar number passed 12th-digit Verhoeff checksum validation."
        )

class AadhaarDOBPlausibilityRule(BaseValidationRule):
    rule_id = "RULE_AADHAAR_DOB"
    rule_name = "Aadhaar Date of Birth Plausibility"
    category = ValidationCategory.DATE_VALIDITY

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not extraction.date_of_birth or not extraction.date_of_birth.value:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Plausible birth year check (1900 <= YOB <= current_year)",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="DOB_MISSING",
                reason="Date of birth field missing."
            )

        dob_str = extraction.date_of_birth.value
        current_year = datetime.now().year
        year = None

        if len(dob_str) == 4 and dob_str.isdigit():
            year = int(dob_str)
        elif "-" in dob_str:
            parts = dob_str.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                year = int(parts[0])

        if year and (year < 1900 or year > current_year):
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Plausible birth year check (1900 <= YOB <= current_year)",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="IMPLAUSIBLE_BIRTH_YEAR",
                field_affected="date_of_birth",
                actual_value=str(year),
                expected_value=f"1900 <= YOB <= {current_year}",
                reason=f"Birth year {year} is out of plausible range (1900-{current_year})."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Plausible birth year check (1900 <= YOB <= current_year)",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="Date of birth is plausibly valid."
        )
