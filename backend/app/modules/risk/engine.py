from typing import List, Dict, Tuple
from app.schemas.evidence import EvidenceBundle
from app.schemas.hypothesis import HypothesisResult
from app.schemas.risk import RiskAssessment, RiskLevel, ReasonCode
from app.schemas.common import SeverityLevel
from app.schemas.validation import RuleStatus
from app.schemas.face import FaceMatchStatus
from app.schemas.database import RegistryStatus
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("risk_engine")

class RiskEngine:
    def __init__(self):
        self.clear_max = settings.RISK_THRESHOLD_CLEAR
        self.review_max = settings.RISK_THRESHOLD_REVIEW

    def compute_risk(
        self,
        bundle: EvidenceBundle,
        hypotheses: HypothesisResult
    ) -> RiskAssessment:
        """Module 12: Deterministic Rule-Based Composite Risk Engine."""
        logger.info("Computing transparent explainable risk score")
        
        reason_codes: List[ReasonCode] = []
        base_score = 0

        val = bundle.validation_result
        tamper = bundle.tamper_result
        fields = bundle.field_mapping_result
        face = bundle.face_result
        db = bundle.database_result

        # Dimension 1: Authenticity Signals (Tampering & Overlaps)
        authenticity_score = 0
        is_tampered = tamper.get("status") != "GENUINE" if tamper else False
        if is_tampered:
            score = tamper.get("tamper_score", 0.0)
            sev = tamper.get("severity", "LOW")
            authenticity_score += int(score * 40)
            reason_codes.append(ReasonCode(
                code="TAMPER_ARTIFACTS_DETECTED",
                description=f"Visual manipulation artifacts detected (Score: {score}, Severity: {sev}).",
                severity=SeverityLevel[sev] if sev in {"LOW", "MEDIUM", "HIGH"} else SeverityLevel.HIGH,
                module_source="TAMPERING_AI",
                weight=25
            ))

        has_tampered_fields = any(item.get("risk") == "HIGH" for item in fields) if fields else False
        if has_tampered_fields:
            highest_field = next((item.get("field") for item in fields if item.get("risk") == "HIGH"), "Unknown")
            overlap_bonus = 35  # Since we map to "HIGH" risk if there is an overlap
            authenticity_score += overlap_bonus
            reason_codes.append(ReasonCode(
                code=f"TAMPER_OVERLAP_{highest_field.upper().replace(' ', '_')}",
                description=f"Pixel-level tampering directly intersects with '{highest_field}' (HIGH).",
                severity=SeverityLevel.HIGH,
                module_source="FIELD_EVIDENCE_MAPPING",
                weight=35
            ))

        # Dimension 2: Validity Signals (Rules, Dates, DB Status)
        validity_score = 0
        if val and val.overall_status == RuleStatus.FAIL:
            validity_score += 45
            reason_codes.append(ReasonCode(
                code="VALIDATION_RULE_FAILURE",
                description="Deterministic checksum or chronological date logic failure.",
                severity=SeverityLevel.HIGH,
                module_source="DETERMINISTIC_VALIDATION",
                weight=45
            ))
        elif val and val.overall_status == RuleStatus.INCONSISTENT:
            validity_score += 20
            reason_codes.append(ReasonCode(
                code="VIZ_MRZ_INCONSISTENCY",
                description="Discrepancy detected between VIZ text and MRZ lines.",
                severity=SeverityLevel.MEDIUM,
                module_source="DETERMINISTIC_VALIDATION",
                weight=20
            ))

        if db and db.status in [RegistryStatus.STOLEN, RegistryStatus.REVOKED, RegistryStatus.WATCHLIST]:
            validity_score += 50
            reason_codes.append(ReasonCode(
                code=f"DATABASE_{db.status.value}",
                description=f"Document flagged as {db.status.value} in registry.",
                severity=SeverityLevel.HIGH,
                module_source="MOCK_DATABASE_INTEL",
                weight=50
            ))

        # Dimension 3: Identity Signals (1:1 Face)
        identity_score = 0
        if face and face.is_conditional_executed:
            if face.match_status == FaceMatchStatus.MISMATCH:
                identity_score += 45
                reason_codes.append(ReasonCode(
                    code="BIOMETRIC_FACE_MISMATCH",
                    description=f"1:1 Face similarity ({face.similarity_score}) below threshold ({face.match_threshold}).",
                    severity=SeverityLevel.HIGH,
                    module_source="FACE_VERIFICATION",
                    weight=45
                ))

        # Total Composite Risk Score (Bounded [0, 100])
        total_risk_score = min(100, authenticity_score + validity_score + identity_score)

        # Categorize Risk Level
        if total_risk_score <= self.clear_max:
            risk_level = RiskLevel.CLEAR
        elif total_risk_score <= self.review_max:
            risk_level = RiskLevel.REVIEW
        else:
            risk_level = RiskLevel.HIGH_RISK

        top_reasons = [rc.description for rc in sorted(reason_codes, key=lambda x: x.weight, reverse=True)[:3]]
        if not top_reasons:
            top_reasons = ["All deterministic checks passed; no tampering or anomalies identified."]

        return RiskAssessment(
            risk_score=total_risk_score,
            risk_level=risk_level,
            reason_codes=reason_codes,
            top_reasons=top_reasons,
            authenticity_score=min(100, authenticity_score),
            validity_score=min(100, validity_score),
            identity_score=min(100, identity_score),
            requires_manual_inspection=risk_level != RiskLevel.CLEAR,
            decision_engine_type="CONFIGURABLE_RULE_MATRIX_NOT_LLM"
        )
