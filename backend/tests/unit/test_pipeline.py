import os
import tempfile
import pytest
import numpy as np
from PIL import Image, ImageDraw

from app.schemas.document import DocumentCategory
from app.schemas.common import BoundingBox
from app.schemas.pipeline import DocumentProcessingResult
from app.schemas.validation import RuleStatus
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.ocr.engine import BaseOCREngine
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline

class MockOCREngine(BaseOCREngine):
    def __init__(self, mock_items):
        self.mock_items = mock_items

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        res = OCRResult(items=self.mock_items, engine_name="MockOCR")
        res.rebuild_full_text()
        return res

def create_sharp_dummy_image() -> str:
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, f"test_pipe_{os.urandom(4).hex()}.png")
    img = Image.new("RGB", (600, 400), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Draw sharp grid lines so OpenCV quality analyzer registers high Laplacian sharpness
    for i in range(0, 600, 15):
        draw.line([(i, 0), (i, 400)], fill=(10, 10, 10), width=2)
    for j in range(0, 400, 15):
        draw.line([(0, j), (600, j)], fill=(10, 10, 10), width=2)
    img.save(path)
    return path

def test_pipeline_synthetic_aadhaar():
    path = create_sharp_dummy_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="GOVERNMENT OF INDIA", confidence=0.99, bounding_box=bbox),
            OCRItem(text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA", confidence=0.98, bounding_box=bbox),
            OCRItem(text="Arjun Sharma", confidence=0.97, bounding_box=bbox),
            OCRItem(text="DOB: 14/05/1992", confidence=0.95, bounding_box=bbox),
            OCRItem(text="GENDER: MALE", confidence=0.99, bounding_box=bbox),
            OCRItem(text="2345 6789 0122", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path, document_id="DOC-PIPE-AADHAAR")

        assert isinstance(res, DocumentProcessingResult)
        assert res.document_id == "DOC-PIPE-AADHAAR"
        assert res.document_type == DocumentCategory.AADHAAR
        assert res.extracted_fields.document_number is not None
        assert res.extracted_fields.document_number.value == "2345 6789 0122"
        assert res.validation.overall_status in (RuleStatus.PASS, RuleStatus.INCONSISTENT)
        assert len(res.evidence) >= 3
        assert res.tampering is not None
        assert hasattr(res.tampering, "tamper_score")

        # Verify evidence items preserve field, data, confidence, bbox, provenance, reason_code
        num_evidence = next(e for e in res.evidence if e.data.get("field") == "aadhaar_number")
        assert num_evidence.confidence > 0.0
        assert num_evidence.provenance is not None
        assert num_evidence.reason_code == "FIELD_EXTRACTED"
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_pipeline_synthetic_driving_licence():
    path = create_sharp_dummy_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="INDIAN DRIVING LICENCE", confidence=0.99, bounding_box=bbox),
            OCRItem(text="MAHARASHTRA MOTOR VEHICLES DEPT", confidence=0.98, bounding_box=bbox),
            OCRItem(text="DL NO: MH-12-20180012345", confidence=0.98, bounding_box=bbox),
            OCRItem(text="NAME: PRIYA SHARMA", confidence=0.96, bounding_box=bbox),
            OCRItem(text="DOB: 20-10-1995", confidence=0.95, bounding_box=bbox),
            OCRItem(text="DOI: 15-01-2018", confidence=0.95, bounding_box=bbox),
            OCRItem(text="VALID TILL: 14-01-2038", confidence=0.95, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path, document_id="DOC-PIPE-DL")

        assert res.document_type in (DocumentCategory.DRIVING_LICENSE, DocumentCategory.DRIVING_LICENCE)
        assert res.extracted_fields.document_number is not None
        assert "MH-12-20180012345" in res.extracted_fields.document_number.value
        assert res.validation.overall_status in (RuleStatus.PASS, RuleStatus.INCONSISTENT)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_pipeline_synthetic_passport_mrz():
    path = create_sharp_dummy_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="PASSPORT", confidence=0.99, bounding_box=bbox),
            OCRItem(text="REPUBLIC OF INDIA", confidence=0.98, bounding_box=bbox),
            OCRItem(text="PASSPORT NO: P8923412", confidence=0.98, bounding_box=bbox),
            OCRItem(text="SURNAME: SHARMA", confidence=0.96, bounding_box=bbox),
            OCRItem(text="GIVEN NAMES: ARJUN", confidence=0.96, bounding_box=bbox),
            OCRItem(text="P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<", confidence=0.99, bounding_box=bbox),
            OCRItem(text="P8923412<8IND9205141M3205138<<<<<<<<<<<0<<<6", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path, document_id="DOC-PIPE-PASS")

        assert res.document_type == DocumentCategory.PASSPORT
        assert res.mrz is not None
        assert res.mrz.is_present is True
        assert res.mrz.document_number == "P8923412"
        assert res.mrz.all_check_digits_valid is True
        assert res.validation.mrz_viz_consistent is True
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_pipeline_unknown_document_controlled_result():
    path = create_sharp_dummy_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="RANDOM TEXT INVOICE RECEIPT", confidence=0.99, bounding_box=bbox),
            OCRItem(text="TOTAL AMOUNT PAID: $500.00", confidence=0.95, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path, document_id="DOC-PIPE-UNK")

        assert res.document_type == DocumentCategory.UNKNOWN
        assert res.extracted_fields.document_category == DocumentCategory.UNKNOWN
        assert res.validation.overall_status in (RuleStatus.PASS, RuleStatus.INCONSISTENT, RuleStatus.NOT_AVAILABLE, RuleStatus.FAIL)
        assert isinstance(res.evidence, list)
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_pipeline_non_existent_file_controlled_result():
    pipeline = DocumentIntelligencePipeline()
    res = pipeline.process_document("non_existent_file_888.jpg", document_id="DOC-PIPE-ERR")

    assert res.document_type == DocumentCategory.UNKNOWN
    assert len(res.errors_or_warnings) >= 1
    assert "File not found" in res.errors_or_warnings[0]
