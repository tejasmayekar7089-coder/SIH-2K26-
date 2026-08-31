import os
import uuid
import re
from typing import Optional, List, Dict, Any

from app.schemas.document import ValidatedInputDocument, DocumentCategory, FileFormat, QualityResult
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult
from app.schemas.metadata import MetadataResult
from app.schemas.validation import ValidationResult
from app.schemas.pipeline import DocumentProcessingResult

from app.modules.acquisition.loader import DocumentLoader
from app.modules.acquisition.quality import QualityAnalyzer
from app.modules.acquisition.preprocessor import ImagePreprocessor
from app.modules.document_intelligence.ocr.engine import BaseOCREngine, PaddleOCREngine
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.modules.document_intelligence.classifier import BaseDocumentClassifier, HeuristicDocumentClassifier
from app.modules.document_intelligence.extractors.base import BaseFieldExtractor
from app.modules.document_intelligence.extractors.aadhaar import AadhaarFieldExtractor, mask_aadhaar_number
from app.modules.document_intelligence.extractors.driving_licence import DrivingLicenceFieldExtractor
from app.modules.document_intelligence.extractors.passport import PassportFieldExtractor
from app.modules.mrz.service import MRZService
from app.modules.metadata.analyzer import IsolatedMetadataAnalyzer
from app.modules.validation.service import ValidationService
from app.modules.evidence.dev1_converter import Developer1EvidenceConverter
from app.modules.fixtures.registry import TestFixtureRegistry
from app.schemas.validation import RuleStatus
from app.core.config import settings
from app.utils.file_utils import detect_file_format, get_mime_type, compute_sha256
from app.core.logging import get_logger

logger = get_logger("document_pipeline")

class DocumentIntelligencePipeline:
    """
    Unified Developer 1 Document Intelligence Pipeline.
    Integrates Acquisition, Quality Analysis, Preprocessing, PaddleOCR, Document Classification,
    Field Extraction, MRZ Processing, Metadata Analysis, Deterministic Validation, and Common Evidence output.
    """

    def __init__(
        self,
        ocr_engine: Optional[BaseOCREngine] = None,
        classifier: Optional[BaseDocumentClassifier] = None,
        mrz_service: Optional[MRZService] = None,
        metadata_analyzer: Optional[IsolatedMetadataAnalyzer] = None,
        validation_service: Optional[ValidationService] = None
    ):
        self.loader = DocumentLoader()
        self.quality_analyzer = QualityAnalyzer()
        self.preprocessor = ImagePreprocessor()
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.classifier = classifier or HeuristicDocumentClassifier()
        self.mrz_service = mrz_service or MRZService()
        self.metadata_analyzer = metadata_analyzer or IsolatedMetadataAnalyzer()
        self.validation_service = validation_service or ValidationService()

        self.extractors: Dict[DocumentCategory, BaseFieldExtractor] = {
            DocumentCategory.AADHAAR: AadhaarFieldExtractor(),
            DocumentCategory.DRIVING_LICENSE: DrivingLicenceFieldExtractor(),
            DocumentCategory.DRIVING_LICENCE: DrivingLicenceFieldExtractor(),
            DocumentCategory.PASSPORT: PassportFieldExtractor()
        }

    def process_document(
        self,
        file_path: str,
        document_id: Optional[str] = None
    ) -> DocumentProcessingResult:
        """
        Main entry point for document intelligence pipeline.
        Exposes process_document() and returns structured Pydantic DocumentProcessingResult.
        """
        doc_id = document_id or f"DOC-{uuid.uuid4().hex[:8].upper()}"
        notices: List[str] = []

        logger.info(f"Starting unified Document Intelligence pipeline for doc ID: {doc_id}")

        # Step 1: Input File Validation
        if not os.path.exists(file_path):
            logger.error(f"Pipeline error: File path does not exist: {file_path}")
            return self._build_controlled_error_result(doc_id, file_path, f"File not found: {file_path}")

        try:
            file_size = os.path.getsize(file_path)
            file_fmt = detect_file_format(os.path.basename(file_path))
            mime = get_mime_type(file_fmt)
            sha256_hash = compute_sha256(file_path)
        except Exception as e:
            logger.error(f"Failed to inspect file attributes for {file_path}: {e}")
            return self._build_controlled_error_result(doc_id, file_path, f"File inspection failed: {e}")

        doc_input = ValidatedInputDocument(
            document_id=doc_id,
            file_name=os.path.basename(file_path),
            file_format=file_fmt,
            mime_type=mime,
            file_size_bytes=file_size,
            sha256_checksum=sha256_hash,
            storage_path=file_path
        )

        file_info = {
            "file_name": doc_input.file_name,
            "file_format": doc_input.file_format.value,
            "mime_type": doc_input.mime_type,
            "file_size_bytes": doc_input.file_size_bytes,
            "sha256": doc_input.sha256_checksum
        }

        # Step 2: Acquisition & Document Loading
        try:
            pages_rgb = self.loader.load_pages_rgb(file_path)
            if not pages_rgb:
                return self._build_controlled_error_result(doc_id, file_path, "Loader returned empty pages.")
            primary_img = pages_rgb[0]
        except Exception as e:
            logger.error(f"Acquisition loader failure for {doc_id}: {e}")
            return self._build_controlled_error_result(doc_id, file_path, f"Document acquisition failed: {e}")

        # Step 3: Quality Analysis
        try:
            quality = self.quality_analyzer.analyze(primary_img)
            logger.info(f"Quality evaluated for {doc_id}: score={quality.quality_score:.2f}, blurred={quality.is_blurred}")
        except Exception as e:
            logger.warning(f"Quality analysis exception for {doc_id}: {e}")
            notices.append(f"Quality analysis failed: {e}")
            quality = QualityResult(quality_score=0.50, blur_score=100.0, is_acceptable=True)

        # Step 4: Non-Destructive Preprocessing
        try:
            prep_img = self.preprocessor.preprocess(primary_img)
        except Exception as e:
            logger.warning(f"Preprocessing exception for {doc_id}: {e}")
            notices.append(f"Preprocessing skipped due to exception: {e}")
            prep_img = primary_img

        # Step 5: OCR Recognition (PaddleOCR)
        try:
            ocr_result = self.ocr_engine.process_image(prep_img, page_index=0)
            logger.info(f"OCR completed for {doc_id}: found {len(ocr_result.items)} text items (mean confidence={ocr_result.mean_confidence:.2f})")
        except Exception as e:
            logger.error(f"OCR engine failure for {doc_id}: {e}")
            notices.append(f"OCR engine error: {e}")
            ocr_result = OCRResult(items=[], full_text="", mean_confidence=0.0)

        # Step 6: Document Classification
        try:
            doc_category, cat_conf = self.classifier.classify(ocr_result, prep_img)
            logger.info(f"Document classified for {doc_id}: category={doc_category.value}, confidence={cat_conf:.2f}")
        except Exception as e:
            logger.warning(f"Classification exception for {doc_id}: {e}")
            doc_category, cat_conf = DocumentCategory.UNKNOWN, 0.0

        # Step 7: Document-Specific Field Extraction (Aadhaar / Driving Licence / Passport / Controlled UNKNOWN)
        extractor = self.extractors.get(doc_category)
        if extractor:
            try:
                extraction = extractor.extract_fields(ocr_result)
                extraction.document_category = doc_category
                extraction.category_confidence = cat_conf
                self._log_extraction_summary_safely(doc_id, doc_category, extraction)
            except Exception as e:
                logger.error(f"Field extraction exception for {doc_id}: {e}")
                notices.append(f"Field extraction exception: {e}")
                extraction = ExtractionResult(document_category=doc_category, category_confidence=cat_conf, raw_text=ocr_result.full_text)
        else:
            # Controlled UNKNOWN response without crashing
            logger.info(f"Category '{doc_category.value}' has no specialized extractor. Returning generic OCR extraction.")
            extraction = ExtractionResult(
                document_category=doc_category,
                category_confidence=cat_conf,
                raw_text=ocr_result.full_text,
                ocr_confidence_mean=ocr_result.mean_confidence
            )

        # Step 8: Passport → MRZ Processing (If Passport)
        mrz_result: Optional[MRZResult] = None
        if doc_category == DocumentCategory.PASSPORT:
            try:
                mrz_result = self.mrz_service.process_passport_mrz(ocr_result, extraction)
                logger.info(f"MRZ processing finished for {doc_id}: present={mrz_result.is_present}, format={mrz_result.mrz_format.value}, valid_checksums={mrz_result.all_check_digits_valid}")
            except Exception as e:
                logger.warning(f"MRZ processing exception for {doc_id}: {e}")
                notices.append(f"MRZ processing failed: {e}")

        # Step 9: Digital File & EXIF Metadata Analysis
        try:
            metadata = self.metadata_analyzer.analyze_file(file_path, document_id=doc_id)
            logger.info(f"Metadata analysis for {doc_id}: classification={metadata.metadata_classification.value}")
        except Exception as e:
            logger.warning(f"Metadata analysis exception for {doc_id}: {e}")
            notices.append(f"Metadata analysis failed: {e}")
            metadata = MetadataResult(
                file_type=doc_input.file_format.value,
                mime_type=doc_input.mime_type,
                file_size_bytes=doc_input.file_size_bytes
            )

        # Step 10: Deterministic Document Validation
        try:
            validation = self.validation_service.perform_deterministic_validation(
                extraction=extraction,
                mrz=mrz_result,
                metadata=metadata,
                quality=quality
            )
            logger.info(f"Validation completed for {doc_id}: status={validation.overall_status.value}, failures={validation.failure_count}, inconsistencies={validation.inconsistency_count}")
        except Exception as e:
            logger.error(f"Deterministic validation exception for {doc_id}: {e}")
            notices.append(f"Validation exception: {e}")
            validation = ValidationResult()

        # Step 10B: Test Fixture Recognition (Development / Demo Mode Only)
        is_fixture = False
        fixture_meta = None
        validation_mode = "STRICT"

        if TestFixtureRegistry.is_fixture_mode_enabled():
            is_fixture, fixture_meta = TestFixtureRegistry.lookup_fixture(file_path)
            if is_fixture and fixture_meta:
                validation_mode = "TEST_FIXTURE"
                validation.validation_mode = "TEST_FIXTURE"
                validation.is_synthetic_fixture = True
                validation.fixture_id = fixture_meta.get("fixture_id")
                validation.fixture_description = fixture_meta.get("description")
                validation.raw_validation_status = validation.overall_status.value
                # Override overall status to PASS specifically for the registered fixture
                validation.overall_status = RuleStatus.PASS
                logger.info(f"Document {doc_id} accepted via TEST_FIXTURE mode (Raw strict status: {validation.raw_validation_status})")
        else:
            logger.info(f"STRICT validation mode active for {doc_id} (DOCUMENT_VALIDATION_MODE={getattr(settings, 'DOCUMENT_VALIDATION_MODE', 'production')})")

        # Step 11: Common Evidence Standard Conversion
        try:
            evidence = Developer1EvidenceConverter.aggregate_dev1_evidence(
                quality=quality,
                extraction=extraction,
                mrz=mrz_result,
                metadata=metadata,
                validation=validation
            )
            logger.info(f"Generated {len(evidence)} common evidence items for {doc_id}")
        except Exception as e:
            logger.error(f"Evidence conversion exception for {doc_id}: {e}")
            notices.append(f"Evidence conversion failed: {e}")
            evidence = []

        return DocumentProcessingResult(
            document_id=doc_id,
            document_type=doc_category,
            file_info=file_info,
            quality=quality,
            ocr=ocr_result,
            extracted_fields=extraction,
            mrz=mrz_result,
            metadata=metadata,
            validation=validation,
            validation_mode=validation_mode,
            is_synthetic_fixture=is_fixture,
            fixture_info=fixture_meta,
            evidence=evidence,
            errors_or_warnings=notices
        )

    def _build_controlled_error_result(self, doc_id: str, file_path: str, error_msg: str) -> DocumentProcessingResult:
        """Returns a controlled DocumentProcessingResult for unreadable or missing files without crashing."""
        quality = QualityResult(quality_score=0.0, blur_score=0.0, is_acceptable=False)
        ocr = OCRResult(items=[], full_text="", mean_confidence=0.0)
        extraction = ExtractionResult(document_category=DocumentCategory.UNKNOWN, category_confidence=0.0)
        metadata = MetadataResult(file_type="UNKNOWN", mime_type="application/octet-stream", file_size_bytes=0)
        validation = ValidationResult()

        return DocumentProcessingResult(
            document_id=doc_id,
            document_type=DocumentCategory.UNKNOWN,
            file_info={"file_name": os.path.basename(file_path)},
            quality=quality,
            ocr=ocr,
            extracted_fields=extraction,
            mrz=None,
            metadata=metadata,
            validation=validation,
            evidence=[],
            errors_or_warnings=[error_msg]
        )

    @classmethod
    def _log_extraction_summary_safely(cls, doc_id: str, category: DocumentCategory, ext: ExtractionResult) -> None:
        """Logs field extraction summary while masking sensitive identity numbers (Aadhaar, Passport)."""
        masked_num = "None"
        if ext.document_number and ext.document_number.value:
            raw_num = ext.document_number.value
            if category == DocumentCategory.AADHAAR:
                masked_num = mask_aadhaar_number(raw_num)
            elif category == DocumentCategory.PASSPORT:
                masked_num = raw_num[:2] + "X" * (len(raw_num) - 4) + raw_num[-2:] if len(raw_num) >= 4 else "X" * len(raw_num)
            else:
                masked_num = raw_num[:3] + "..."

        name_str = ext.full_name.value if ext.full_name else "None"
        logger.info(f"Field extraction for {doc_id} [{category.value}]: DocNumber={masked_num}, Name={name_str}")
