from typing import List, Optional
from app.schemas.document import DocumentCategory, QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import ValidationResult, RuleStatus, RuleEvaluation
from app.modules.validation.registry import DocumentValidatorRegistry, BaseValidationRule
from app.modules.validation.rules.base_rules import QualityRule, OCRConfidenceRule, MetadataRule
from app.modules.validation.rules.aadhaar_rules import AadhaarPresenceRule, AadhaarVerhoeffRule, AadhaarDOBPlausibilityRule
from app.modules.validation.rules.dl_rules import DLPresenceRule, DLFormatRule, DLDateChronologyRule
from app.modules.validation.rules.passport_rules import PassportPresenceRule, PassportMRZCheckDigitRule, PassportOCZMRZConsistencyRule
from app.core.logging import get_logger

logger = get_logger("validation")

class ValidationService:
    """Module 5: Pure Deterministic Rule-Based Document & Cross-Field Validation Engine."""

    def __init__(self, registry: Optional[DocumentValidatorRegistry] = None):
        self.registry = registry or self._build_default_registry()

    def _build_default_registry(self) -> DocumentValidatorRegistry:
        reg = DocumentValidatorRegistry()

        # Shared base rules
        quality_rule = QualityRule()
        ocr_rule = OCRConfidenceRule()
        meta_rule = MetadataRule()

        # 1. Aadhaar Rule Set
        reg.register_rule(DocumentCategory.AADHAAR, quality_rule)
        reg.register_rule(DocumentCategory.AADHAAR, ocr_rule)
        reg.register_rule(DocumentCategory.AADHAAR, meta_rule)
        reg.register_rule(DocumentCategory.AADHAAR, AadhaarPresenceRule())
        reg.register_rule(DocumentCategory.AADHAAR, AadhaarVerhoeffRule())
        reg.register_rule(DocumentCategory.AADHAAR, AadhaarDOBPlausibilityRule())

        # 2. Driving Licence Rule Set
        for cat in (DocumentCategory.DRIVING_LICENSE, DocumentCategory.DRIVING_LICENCE):
            reg.register_rule(cat, quality_rule)
            reg.register_rule(cat, ocr_rule)
            reg.register_rule(cat, meta_rule)
            reg.register_rule(cat, DLPresenceRule())
            reg.register_rule(cat, DLFormatRule())
            reg.register_rule(cat, DLDateChronologyRule())

        # 3. Passport Rule Set
        reg.register_rule(DocumentCategory.PASSPORT, quality_rule)
        reg.register_rule(DocumentCategory.PASSPORT, ocr_rule)
        reg.register_rule(DocumentCategory.PASSPORT, meta_rule)
        reg.register_rule(DocumentCategory.PASSPORT, PassportPresenceRule())
        reg.register_rule(DocumentCategory.PASSPORT, PassportMRZCheckDigitRule())
        reg.register_rule(DocumentCategory.PASSPORT, PassportOCZMRZConsistencyRule())

        # 4. Unknown / Generic Rule Set
        reg.register_rule(DocumentCategory.UNKNOWN, quality_rule)
        reg.register_rule(DocumentCategory.UNKNOWN, ocr_rule)
        reg.register_rule(DocumentCategory.UNKNOWN, meta_rule)

        return reg

    def perform_deterministic_validation(
        self,
        extraction: ExtractionResult,
        mrz: Optional[MRZResult] = None,
        metadata: Optional[MetadataResult] = None,
        quality: Optional[QualityResult] = None
    ) -> ValidationResult:
        """
        Executes deterministic, rule-based validation checks on extracted document attributes.
        Deterministic guarantee: same input -> exact same output.
        """
        category = extraction.document_category if extraction else DocumentCategory.UNKNOWN
        logger.info(f"Executing deterministic validation checks for category: '{category.value}'")

        rules = self.registry.get_rules_for_category(category)
        evaluations: List[RuleEvaluation] = []

        for rule in rules:
            try:
                eval_res = rule.evaluate(
                    extraction=extraction,
                    mrz=mrz,
                    metadata=metadata,
                    quality=quality
                )
                evaluations.append(eval_res)
            except Exception as e:
                logger.error(f"Rule evaluation error for '{rule.rule_id}': {e}")
                evaluations.append(RuleEvaluation(
                    rule_id=rule.rule_id,
                    rule_name=rule.rule_name,
                    category=rule.category,
                    description=f"Error evaluating rule {rule.rule_id}",
                    status=RuleStatus.FAIL,
                    severity="HIGH",
                    reason_code="RULE_EVALUATION_ERROR",
                    reason=f"Internal rule evaluation exception: {e}"
                ))

        # Determine overall status
        has_fail = any(e.status == RuleStatus.FAIL for e in evaluations)
        has_inconsistent = any(e.status == RuleStatus.INCONSISTENT for e in evaluations)

        if has_fail:
            overall = RuleStatus.FAIL
        elif has_inconsistent:
            overall = RuleStatus.INCONSISTENT
        else:
            overall = RuleStatus.PASS

        format_valid = not any(e.status == RuleStatus.FAIL and e.category == "FIELD_FORMAT" for e in evaluations)
        date_logic_valid = not any(e.status == RuleStatus.FAIL and e.category == "DATE_ORDERING" for e in evaluations)
        mrz_viz_consistent = not any(e.status in (RuleStatus.FAIL, RuleStatus.INCONSISTENT) and e.category in ("MRZ_CHECK_DIGITS", "OCR_MRZ_CONSISTENCY") for e in evaluations)

        fail_count = sum(1 for e in evaluations if e.status == RuleStatus.FAIL)
        inconsistent_count = sum(1 for e in evaluations if e.status == RuleStatus.INCONSISTENT)

        return ValidationResult(
            overall_status=overall,
            format_valid=format_valid,
            date_logic_valid=date_logic_valid,
            mrz_viz_consistent=mrz_viz_consistent,
            evaluations=evaluations,
            inconsistency_count=inconsistent_count,
            failure_count=fail_count,
            summary_notes="Deterministic rule engine completed. Results provide evidence reason codes for downstream hypothesis evaluation."
        )
