from typing import Optional
from app.schemas.document import QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult, MetadataClassification
from app.schemas.validation import RuleEvaluation, RuleStatus, ValidationCategory
from app.modules.validation.registry import BaseValidationRule

class QualityRule(BaseValidationRule):
    rule_id = "RULE_QUAL_01"
    rule_name = "Document Quality & Blur Inspection"
    category = ValidationCategory.DOCUMENT_QUALITY

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not quality:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Image quality score & blur inspection",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="QUALITY_DATA_NOT_AVAILABLE",
                reason="Image quality metric data unavailable."
            )

        if quality.quality_score < 0.50:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Image quality score & blur inspection",
                status=RuleStatus.FAIL,
                severity="HIGH",
                reason_code="LOW_IMAGE_QUALITY",
                actual_value=f"Score: {quality.quality_score:.2f}",
                expected_value=">= 0.50",
                reason=f"Image quality score ({quality.quality_score:.2f}) is below minimum acceptable threshold (0.50)."
            )

        if quality.is_blurred:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Image quality score & blur inspection",
                status=RuleStatus.INCONSISTENT,
                severity="MEDIUM",
                reason_code="IMAGE_BLUR_DETECTED",
                actual_value=f"Blur score: {quality.blur_score:.1f}",
                reason="Severe image blur detected which may impair OCR precision."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Image quality score & blur inspection",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="Image quality score and sharpness are satisfactory."
        )

class OCRConfidenceRule(BaseValidationRule):
    rule_id = "RULE_OCR_01"
    rule_name = "OCR Text Recognition Confidence"
    category = ValidationCategory.OCR_CONFIDENCE

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not extraction or extraction.ocr_confidence_mean <= 0.0:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="OCR mean recognition confidence threshold",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="NO_OCR_TEXT",
                reason="No readable OCR text detected in document."
            )

        if extraction.ocr_confidence_mean < 0.55:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="OCR mean recognition confidence threshold",
                status=RuleStatus.INCONSISTENT,
                severity="MEDIUM",
                reason_code="LOW_OCR_CONFIDENCE",
                actual_value=f"{extraction.ocr_confidence_mean:.2f}",
                expected_value=">= 0.55",
                reason=f"Mean OCR confidence ({extraction.ocr_confidence_mean:.2f}) is below confidence threshold (0.55)."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="OCR mean recognition confidence threshold",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="OCR text recognition confidence is high."
        )

class MetadataRule(BaseValidationRule):
    rule_id = "RULE_META_01"
    rule_name = "EXIF Metadata Signature Verification"
    category = ValidationCategory.INTERNAL_CONSISTENCY

    def evaluate(self, extraction: ExtractionResult, mrz: Optional[MRZResult] = None, metadata: Optional[MetadataResult] = None, quality: Optional[QualityResult] = None) -> RuleEvaluation:
        if not metadata:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Digital EXIF metadata analysis",
                status=RuleStatus.NOT_AVAILABLE,
                severity="LOW",
                reason_code="METADATA_NOT_AVAILABLE",
                reason="Digital metadata unavailable."
            )

        if metadata.metadata_classification == MetadataClassification.SUSPICIOUS_METADATA:
            return RuleEvaluation(
                rule_id=self.rule_id,
                rule_name=self.rule_name,
                category=self.category,
                description="Digital EXIF metadata analysis",
                status=RuleStatus.INCONSISTENT,
                severity="MEDIUM",
                reason_code="SUSPICIOUS_METADATA_SOFTWARE",
                actual_value=metadata.software_signature or "Editing Software Tag",
                reason="EXIF tags contain image editing software signatures. Supporting evidence only."
            )

        return RuleEvaluation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            description="Digital EXIF metadata analysis",
            status=RuleStatus.PASS,
            severity="LOW",
            reason_code="CHECK_PASSED",
            reason="Digital metadata contains no editing software anomalies."
        )
