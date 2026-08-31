import time
from datetime import datetime, timezone
from typing import Optional
from app.schemas.document import ValidatedInputDocument
from app.schemas.screening import ScreeningResponse, ScreeningStatus, OfficerAction
from app.modules.acquisition.service import AcquisitionService
from app.modules.document_intelligence.service import DocumentIntelligenceService
from app.modules.mrz.service import MRZService
from app.modules.metadata.service import MetadataService
from app.modules.validation.service import ValidationService
from app.modules.tampering.service import TamperingAIService
from app.modules.field_mapping.service import FieldMappingService
from app.modules.face.service import FaceVerificationService
from app.modules.external_intelligence.service import ExternalIntelligenceService
from app.modules.evidence.builder import EvidenceBuilderService
from app.modules.hypothesis.engine import FraudHypothesisEngine
from app.modules.risk.engine import RiskEngine
from app.modules.audit.service import AuditTrailService
from app.core.logging import get_logger

logger = get_logger("pipeline_orchestrator")

class ScreeningPipelineOrchestrator:
    def __init__(self):
        # Initialize all 14 pipeline modules
        self.acquisition_service = AcquisitionService()
        self.doc_intel_service = DocumentIntelligenceService()
        self.mrz_service = MRZService()
        self.metadata_service = MetadataService()
        self.validation_service = ValidationService()
        self.tampering_service = TamperingAIService()
        self.field_mapping_service = FieldMappingService()
        self.face_service = FaceVerificationService()
        self.external_intel_service = ExternalIntelligenceService()
        self.evidence_builder = EvidenceBuilderService()
        self.hypothesis_engine = FraudHypothesisEngine()
        self.risk_engine = RiskEngine()
        self.audit_service = AuditTrailService()

    async def execute_screening(
        self,
        screening_id: str,
        doc_input: ValidatedInputDocument
    ) -> ScreeningResponse:
        """Executes full 14-module pipeline asynchronously."""
        start_time = time.time()
        logger.info(f"Starting pipeline execution for: {screening_id}")

        try:
            # Module 2: Acquisition & Quality
            quality_result = self.acquisition_service.evaluate_and_preprocess(doc_input)
            active_image_path = quality_result.processed_image_path

            # Module 3: Document Intelligence (OCR + Layout + Portrait Crop)
            extraction_result = self.doc_intel_service.extract_document_features(doc_input, active_image_path)

            # Module 4A: MRZ Parsing
            mrz_result = self.mrz_service.parse_and_validate(extraction_result)

            # Module 4B: Metadata Analysis (Supporting evidence only)
            metadata_result = self.metadata_service.extract_metadata(doc_input)

            # Module 5: Deterministic Document Validation
            validation_result = self.validation_service.perform_deterministic_validation(
                extraction_result, mrz_result, metadata_result
            )

            # Module 6: Tampering AI (Core AI Innovation)
            tamper_result = self.tampering_service.analyze_tampering(doc_input, active_image_path)

            # Module 7: Field-Evidence Mapping
            field_mapping_result = self.field_mapping_service.map_tamper_to_fields(
                extraction_result, tamper_result
            )

            # Module 8: Conditional 1:1 Face Verification
            face_result = self.face_service.verify_identity(doc_input, extraction_result)

            # Module 9: Mock External Intelligence
            database_result = self.external_intel_service.query_document_status(extraction_result)

            # Module 10: Evidence Builder (Normalizer)
            evidence_bundle = self.evidence_builder.build_evidence_bundle(
                screening_id=screening_id,
                quality=quality_result,
                extraction=extraction_result,
                mrz=mrz_result,
                metadata=metadata_result,
                validation=validation_result,
                tampering=tamper_result,
                field_mapping=field_mapping_result,
                face=face_result,
                database=database_result
            )

            # Module 11: Fraud Hypothesis Engine
            hypothesis_result = self.hypothesis_engine.evaluate_hypotheses(evidence_bundle)

            # Module 12: Risk Engine
            risk_assessment = self.risk_engine.compute_risk(evidence_bundle, hypothesis_result)

            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            response = ScreeningResponse(
                screening_id=screening_id,
                status=ScreeningStatus.COMPLETED,
                timestamp_utc=datetime.now(timezone.utc),
                processing_time_ms=elapsed_ms,
                document_info=doc_input,
                risk_assessment=risk_assessment,
                hypothesis_result=hypothesis_result,
                evidence_bundle=evidence_bundle,
                officer_action_state=OfficerAction.PENDING,
                officer_statement="AI ASSISTS • OFFICER DECIDES"
            )

            # Module 14: Audit Trail Logging
            await self.audit_service.log_screening_event(response)

            logger.info(f"Pipeline finished for {screening_id} in {elapsed_ms}ms with Risk Level: {risk_assessment.risk_level.value}")
            return response

        except Exception as e:
            logger.exception(f"Pipeline error during execution for {screening_id}: {e}")
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            return ScreeningResponse(
                screening_id=screening_id,
                status=ScreeningStatus.FAILED,
                timestamp_utc=datetime.now(timezone.utc),
                processing_time_ms=elapsed_ms,
                document_info=doc_input,
                officer_action_state=OfficerAction.PENDING,
                officer_statement=f"AI ASSISTS • OFFICER DECIDES (Pipeline Error: {str(e)})"
            )
