import os
import cv2
import numpy as np
import pytest

from app.schemas.document import DocumentCategory
from app.modules.document_intelligence.ocr.engine import PaddleOCREngine
from app.modules.mrz.detector import MRZDetector
from app.modules.mrz.parser import TD3MRZParser
from app.modules.mrz.validator import ICAO9303Validator
from app.modules.document_intelligence.extractors.passport import PassportFieldExtractor
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.modules.fixtures.registry import TestFixtureRegistry

def create_synthetic_passport_image() -> np.ndarray:
    """Generates a synthetic passport specimen image for real OCR testing."""
    img = np.ones((500, 900, 3), dtype=np.uint8) * 255
    # Border
    cv2.rectangle(img, (20, 20), (880, 480), (0, 0, 0), 2)
    # Header
    cv2.putText(img, 'PASSPORT', (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 3)
    cv2.putText(img, 'REPUBLIC OF INDIA', (250, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
    # VIZ Details
    cv2.putText(img, 'PASSPORT NO: Z1234567', (50, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'SURNAME: SHARMA', (50, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'GIVEN NAMES: RAHUL', (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'NATIONALITY: INDIAN', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'DATE OF BIRTH: 01/01/1990', (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'SEX / SEX M', (550, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'DATE OF ISSUE: 01/01/2015', (50, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, 'DATE OF EXPIRY: 01/01/2025', (450, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    # MRZ Lines
    cv2.putText(img, 'P<INDSHARMA<<RAHUL<<<<<<<<<<<<<<<<<<<<<<<<<<', (40, 400), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    cv2.putText(img, 'Z1234567<4IND9001011M2501017<<<<<<<<<<<<<<<04', (40, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2)
    return img

def test_real_ocr_synthetic_image():
    img = create_synthetic_passport_image()
    engine = PaddleOCREngine()
    ocr_res = engine.process_image(img)

    assert ocr_res is not None
    assert len(ocr_res.items) > 0
    assert ocr_res.mean_confidence > 0.0
    assert "PASSPORT" in ocr_res.full_text.upper()

def test_mrz_detection_and_parsing_real_ocr():
    img = create_synthetic_passport_image()
    engine = PaddleOCREngine()
    ocr_res = engine.process_image(img)

    detector = MRZDetector()
    raw_lines, bbox = detector.detect_mrz(ocr_res)

    assert len(raw_lines) == 2
    assert raw_lines[0].startswith("P<")
    assert "SHARMA" in raw_lines[0]

    parsed = TD3MRZParser.parse(raw_lines)
    assert parsed.mrz_format.value == "TD3"
    assert parsed.surname == "SHARMA"
    assert parsed.given_names == "RAHUL"
    assert parsed.passport_number == "Z1234567"
    assert parsed.nationality == "IND"

    validator = ICAO9303Validator()
    verifications, all_valid = validator.validate_mrz_data(parsed)
    assert isinstance(all_valid, bool)

def test_passport_field_extractor():
    img = create_synthetic_passport_image()
    engine = PaddleOCREngine()
    ocr_res = engine.process_image(img)

    extractor = PassportFieldExtractor()
    extraction = extractor.extract_fields(ocr_res)

    assert extraction.document_category == DocumentCategory.PASSPORT
    assert extraction.document_number is not None
    assert extraction.document_number.value == "Z1234567"
    assert extraction.full_name is not None
    assert "SHARMA" in extraction.full_name.value.upper()

def test_pipeline_process_document(tmp_path):
    img = create_synthetic_passport_image()
    img_path = os.path.join(tmp_path, "synthetic_passport.png")
    cv2.imwrite(str(img_path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

    pipeline = DocumentIntelligencePipeline()
    result = pipeline.process_document(file_path=str(img_path))

    assert result.document_id is not None
    assert result.document_type == DocumentCategory.PASSPORT
    assert result.ocr is not None
    assert len(result.ocr.items) > 0
    assert result.extracted_fields.document_number is not None
    assert result.extracted_fields.document_number.value == "Z1234567"
    assert result.mrz is not None
    assert result.mrz.is_present is True

def test_unreadable_file_handling(tmp_path):
    bad_file = os.path.join(tmp_path, "non_existent.png")
    pipeline = DocumentIntelligencePipeline()
    result = pipeline.process_document(file_path=str(bad_file))

    assert result.document_type == DocumentCategory.UNKNOWN
    assert len(result.ocr.items) == 0
    assert len(result.errors_or_warnings) > 0
