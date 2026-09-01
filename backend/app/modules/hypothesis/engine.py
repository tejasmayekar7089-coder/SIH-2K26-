from typing import List, Optional
from app.schemas.evidence import EvidenceBundle
from app.schemas.hypothesis import HypothesisResult, FraudHypothesis, HypothesisType
from app.schemas.common import SeverityLevel
from app.schemas.validation import RuleStatus
from app.schemas.face import FaceMatchStatus
from app.schemas.database import RegistryStatus
from app.core.logging import get_logger

logger = get_logger("hypothesis_engine")

class FraudHypothesisEngine:
    def __init__(self):
        pass

    def evaluate_hypotheses(self, bundle: EvidenceBundle) -> HypothesisResult:
        """Module 11: Fraud Hypothesis Deductive Reasoning Engine."""
        logger.info("Evaluating multi-signal fraud hypotheses")
        hypotheses: List[FraudHypothesis] = []

        validation = bundle.validation_result
        tampering = bundle.tamper_result
        field_mapping = bundle.field_mapping_result
        face = bundle.face_result
        db = bundle.database_result

        # Hypothesis 1: Altered Field
        # Trigger: VIZ != MRZ or Tamper Overlap on crucial fields
        has_tampered_fields = any(item.get("risk") == "HIGH" for item in field_mapping) if field_mapping else False
        highest_risk_field = next((item.get("field") for item in field_mapping if item.get("risk") == "HIGH"), "Unknown") if field_mapping else "Unknown"

        if has_tampered_fields:
            hypotheses.append(FraudHypothesis(
                hypothesis_type=HypothesisType.ALTERED_FIELD,
                title="Suspected Document Text Alteration",
                description=f"Pixel-level tampering detected overlapping with field: '{highest_risk_field}'.",
                confidence=0.91,
                severity=SeverityLevel.HIGH,
                supporting_evidence_ids=["TAMPERING_AI", "FIELD_EVIDENCE_MAPPING"],
                reasoning="Co-localization of frequency-domain artifacts with OCR bounding box."
            ))
        elif validation and validation.mrz_viz_consistent is False:
            hypotheses.append(FraudHypothesis(
                hypothesis_type=HypothesisType.ALTERED_FIELD,
                title="Inconsistent VIZ and MRZ Data",
                description="Visual inspection zone text does not match machine-readable zone.",
                confidence=0.88,
                severity=SeverityLevel.MEDIUM,
                supporting_evidence_ids=["DETERMINISTIC_VALIDATION"],
                reasoning="Checksum or field reconciliation discrepancy between VIZ and MRZ."
            ))

        # Hypothesis 2: Photo Replacement
        # Trigger: Tamper overlap on portrait region OR Face mismatch with high tampering
        is_tampered = tampering.get("status") != "GENUINE" if tampering else False

        if face and face.match_status == FaceMatchStatus.MISMATCH and is_tampered:
            hypotheses.append(FraudHypothesis(
                hypothesis_type=HypothesisType.PHOTO_REPLACEMENT,
                title="Suspected Portrait Photo Replacement",
                description="Biometric face mismatch combined with visual tampering signatures on document.",
                confidence=0.94,
                severity=SeverityLevel.HIGH,
                supporting_evidence_ids=["FACE_VERIFICATION", "TAMPERING_AI"],
                reasoning="Discrepancy in facial geometry coupled with edge/noise artifacts around photo box."
            ))

        # Hypothesis 3: Impersonation
        # Trigger: Document is authentic/clean, but live traveller does not match portrait
        if face and face.match_status == FaceMatchStatus.MISMATCH and not is_tampered:
            hypotheses.append(FraudHypothesis(
                hypothesis_type=HypothesisType.IMPERSONATION,
                title="Possible Impersonation / Lookalike Fraud",
                description="The presented document appears authentic, but the traveller's live face does not match.",
                confidence=0.89,
                severity=SeverityLevel.HIGH,
                supporting_evidence_ids=["FACE_VERIFICATION"],
                reasoning="1:1 ArcFace cosine similarity fell below threshold on an unmodified genuine document."
            ))

        # Hypothesis 4: Status Fraud
        # Trigger: Document number is flagged in registry
        if db and db.status in [RegistryStatus.STOLEN, RegistryStatus.LOST, RegistryStatus.REVOKED, RegistryStatus.WATCHLIST]:
            hypotheses.append(FraudHypothesis(
                hypothesis_type=HypothesisType.STATUS_FRAUD,
                title="Invalid Document Status Alert",
                description=f"Document status returned '{db.status.value}' from registry query.",
                confidence=1.0,
                severity=SeverityLevel.HIGH,
                supporting_evidence_ids=["MOCK_DATABASE_INTEL"],
                reasoning=f"Registry alert: {db.remarks}"
            ))

        primary = hypotheses[0].hypothesis_type if hypotheses else None

        return HypothesisResult(
            active_hypotheses=hypotheses,
            has_fraud_suspicions=len(hypotheses) > 0,
            primary_hypothesis=primary
        )
