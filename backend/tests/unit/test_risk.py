import pytest
from app.modules.risk.engine import RiskEngine
from app.schemas.evidence import EvidenceBundle
from app.schemas.hypothesis import HypothesisResult, FraudHypothesis, HypothesisType
from app.schemas.validation import ValidationResult, RuleStatus
from app.schemas.tampering import TamperResult, TamperModelSource
from app.schemas.field_mapping import FieldMappingResult
from app.schemas.face import FaceResult, FaceMatchStatus
from app.schemas.database import DatabaseResult, RegistryStatus
from app.schemas.risk import RiskLevel

def test_risk_engine_clear():
    engine = RiskEngine()
    bundle = EvidenceBundle(
        screening_id="TEST-01",
        validation_result=ValidationResult(overall_status=RuleStatus.PASS),
        tamper_result=TamperResult(model_used=TamperModelSource.DOCTAMPER, is_tampered=False, tamper_score=0.08),
        field_mapping_result=FieldMappingResult(has_tampered_fields=False),
        face_result=FaceResult(match_status=FaceMatchStatus.MATCH, similarity_score=0.92),
        database_result=DatabaseResult(status=RegistryStatus.VALID)
    )
    hypotheses = HypothesisResult(has_fraud_suspicions=False)
    
    assessment = engine.compute_risk(bundle, hypotheses)
    assert assessment.risk_level == RiskLevel.CLEAR
    assert assessment.risk_score <= 29

def test_risk_engine_high_risk_on_stolen():
    engine = RiskEngine()
    bundle = EvidenceBundle(
        screening_id="TEST-02",
        validation_result=ValidationResult(overall_status=RuleStatus.PASS),
        tamper_result=TamperResult(model_used=TamperModelSource.DOCTAMPER, is_tampered=False, tamper_score=0.10),
        field_mapping_result=FieldMappingResult(has_tampered_fields=False),
        face_result=FaceResult(match_status=FaceMatchStatus.MATCH, similarity_score=0.90),
        database_result=DatabaseResult(status=RegistryStatus.STOLEN)
    )
    hypotheses = HypothesisResult(has_fraud_suspicions=True)
    
    assessment = engine.compute_risk(bundle, hypotheses)
    assert assessment.risk_level == RiskLevel.HIGH_RISK or assessment.risk_level == RiskLevel.REVIEW
    assert any("STOLEN" in rc.code for rc in assessment.reason_codes)
