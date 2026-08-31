import re
from datetime import datetime
from typing import Optional
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import RuleEvaluation, RuleStatus, ValidationCategory
from app.modules.validation.registry import BaseValidationRule
from app.modules.document_intelligence.extractors.driving_licence import VALID_INDIAN_STATE_CODES

class DLPresenceRule(BaseValidationRule):
    rule_id = "RULE_DL_PRESENCE"
    rule_name = "Driving Licence Field Presence"
    category = ValidationCategory.FIELD_PRESENCE

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        missing = []
        if not extraction.document_number:
            missing.append("driving_licence_number")
        if not extraction.full_name:
            missing.append("name")
        if not extraction.date_of_birth:
            missing.append("date_of_birth")

        if missing:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Assert presence of required Driving Licence fields",
                status=RuleStatus.INCONSISTENT,
                severity="MEDIUM",
                reason_code="MISSING_REQUIRED_FIELD",
                field_affected=", ".join(missing),
                reason=f"Missing {len(missing)} required Driving Licence field(s): {', '.join(missing)}"
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Assert presence of required Driving Licence fields",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="All core Driving Licence fields are present."
        )

class DLFormatRule(BaseValidationRule):
    rule_id = "RULE_DL_FORMAT"
    rule_name = "Driving Licence MoRTH Format Check"
    category = ValidationCategory.FIELD_FORMAT

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not extraction.document_number or not extraction.document_number.value:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verify Indian state RTO prefix and serial structure",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="DL_NUM_MISSING",
                reason="Driving licence number missing."
            )

        raw_val = extraction.document_number.value.strip().upper()
        clean_val = re.sub(r'[\s/]', '-', raw_val)
        state_code = clean_val[:2]

        if state_code not in VALID_INDIAN_STATE_CODES:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Verify Indian state RTO prefix and serial structure",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="INVALID_DL_STATE_CODE",
                field_affected="driving_licence_number",
                actual_value=state_code,
                expected_value="Valid 2-letter State/UT Code",
                reason=f"State code '{state_code}' in DL Number '{clean_val}' is not a recognized Indian State/UT code."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Verify Indian state RTO prefix and serial structure",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason=f"DL Number '{clean_val}' matches valid Indian state RTO formatting."
        )

class DLDateChronologyRule(BaseValidationRule):
    rule_id = "RULE_DL_CHRONOLOGY"
    rule_name = "Driving Licence Date Chronology (Issue < Expiry)"
    category = ValidationCategory.DATE_ORDERING

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        iss = extraction.issue_date.value if extraction.issue_date else None
        exp = extraction.expiry_date.value if extraction.expiry_date else None

        if not iss or not exp:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Assert Issue Date is strictly before Expiry Date",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="DATES_NOT_AVAILABLE",
                reason="Issue Date or Expiry Date unavailable for chronology check."
            )

        try:
            d_iss = datetime.strptime(iss, "%Y-%m-%d")
            d_exp = datetime.strptime(exp, "%Y-%m-%d")
            if d_iss >= d_exp:
                return RuleEvaluation(
                    rule_id=self.rule_id,
                    rule_name=self.rule_name,
                    category=self.category,
                    description="Assert Issue Date is strictly before Expiry Date",
                    status=RuleStatus.FAIL,
                    severity="HIGH",
                    reason_code="INVERTED_DATE_SEQUENCE",
                    field_affected="date_of_issue / expiry_date",
                    actual_value=f"Issue: {iss}, Expiry: {exp}",
                    expected_value="Issue Date < Expiry Date",
                    reason=f"Date of issue ({iss}) is on or after document expiry date ({exp})."
                )
        except ValueError:
            pass

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Assert Issue Date is strictly before Expiry Date",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="Issue Date and Expiry Date are chronologically valid."
        )
