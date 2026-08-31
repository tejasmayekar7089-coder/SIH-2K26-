import os
import tempfile
import pytest
import numpy as np
from PIL import Image, ImageDraw

from app.schemas.document import DocumentCategory
from app.schemas.common import BoundingBox
from app.schemas.validation import RuleStatus
from app.schemas.mrz import ConsistencyStatus
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.ocr.engine import BaseOCREngine
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.modules.acquisition.quality import QualityAnalyzer
from app.modules.acquisition.loader import DocumentLoader
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class MockOCREngine(BaseOCREngine):
    def __init__(self, mock_items):
        self.mock_items = mock_items

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        res = OCRResult(items=self.mock_items, engine_name="MockOCR")
        res.rebuild_full_text()
        return res

def create_test_image(width=600, height=400, blur=False, dpi=None) -> str:
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, f"stab_test_{os.urandom(4).hex()}.png")

    if blur:
        # Create solid gray image with 0 edge variance for high blur score
        img = Image.new("RGB", (width, height), color=(128, 128, 128))
    else:
        img = Image.new("RGB", (width, height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        for i in range(0, width, 15):
            draw.line([(i, 0), (i, height)], fill=(10, 10, 10), width=2)
        for j in range(0, height, 15):
            draw.line([(0, j), (width, j)], fill=(10, 10, 10), width=2)

    save_kwargs = {}
    if dpi:
        save_kwargs["dpi"] = dpi

    img.save(path, **save_kwargs)
    return path

# 1. Aadhaar Synthetic Sample
def test_scenario_01_aadhaar_synthetic():
    path = create_test_image()
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
        res = pipeline.process_document(path)
        assert res.document_type == DocumentCategory.AADHAAR
        assert res.extracted_fields.document_number.value == "2345 6789 0122"
        assert res.validation.overall_status in (RuleStatus.PASS, RuleStatus.INCONSISTENT)
    finally:
        if os.path.exists(path): os.remove(path)

# 2. Driving Licence Synthetic Sample
def test_scenario_02_dl_synthetic():
    path = create_test_image()
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
        res = pipeline.process_document(path)
        assert res.document_type in (DocumentCategory.DRIVING_LICENSE, DocumentCategory.DRIVING_LICENCE)
        assert "MH-12-20180012345" in res.extracted_fields.document_number.value
    finally:
        if os.path.exists(path): os.remove(path)

# 3. Passport Synthetic Sample
def test_scenario_03_passport_synthetic():
    path = create_test_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="PASSPORT", confidence=0.99, bounding_box=bbox),
            OCRItem(text="REPUBLIC OF INDIA", confidence=0.98, bounding_box=bbox),
            OCRItem(text="PASSPORT NO: P8923412", confidence=0.98, bounding_box=bbox),
            OCRItem(text="SURNAME: SHARMA", confidence=0.96, bounding_box=bbox),
            OCRItem(text="P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<", confidence=0.99, bounding_box=bbox),
            OCRItem(text="P8923412<8IND9205141M3205138<<<<<<<<<<<0<<<6", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path)
        assert res.document_type == DocumentCategory.PASSPORT
        assert res.mrz is not None
        assert res.mrz.is_present is True
    finally:
        if os.path.exists(path): os.remove(path)

# 4. Invalid Image Handling
def test_scenario_04_invalid_image():
    files = {"document_file": ("corrupt.png", b"NOT_AN_IMAGE_PAYLOAD", "image/png")}
    response = client.post("/api/v1/documents/analyze", files=files)
    assert response.status_code == 400
    assert "Corrupted or unreadable image file" in response.json()["detail"]

# 5. Blurry Image Detection
def test_scenario_05_blurry_image():
    path = create_test_image(blur=True)
    try:
        pages = DocumentLoader.load_pages_rgb(path)
        analyzer = QualityAnalyzer()
        res = analyzer.analyze(pages[0])
        assert res.is_blurred is True or res.blur_score < 100.0
    finally:
        if os.path.exists(path): os.remove(path)

# 6. Low-Resolution Image Detection
def test_scenario_06_low_resolution_image():
    path = create_test_image(width=100, height=80, dpi=(72, 72))
    try:
        pages = DocumentLoader.load_pages_rgb(path)
        analyzer = QualityAnalyzer()
        res = analyzer.analyze(pages[0])
        assert res.resolution_dpi < 150 or res.quality_score < 0.8
    finally:
        if os.path.exists(path): os.remove(path)

# 7. Unknown Document
def test_scenario_07_unknown_document():
    path = create_test_image()
    try:
        items = [OCRItem(text="GROCERY STORE INVOICE RECEIPT", confidence=0.99)]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path)
        assert res.document_type == DocumentCategory.UNKNOWN
        assert isinstance(res.errors_or_warnings, list)
    finally:
        if os.path.exists(path): os.remove(path)

# 8. Passport with Valid MRZ
def test_scenario_08_passport_valid_mrz():
    path = create_test_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="PASSPORT NO: P8923412", confidence=0.98, bounding_box=bbox),
            OCRItem(text="P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<", confidence=0.99, bounding_box=bbox),
            OCRItem(text="P8923412<8IND9205141M3205138<<<<<<<<<<<0<<<6", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path)
        assert res.mrz.all_check_digits_valid is True
    finally:
        if os.path.exists(path): os.remove(path)

# 9. Passport with Invalid MRZ Check Digit
def test_scenario_09_passport_invalid_mrz_checksum():
    path = create_test_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        # Corrupted check digit (expected 8, provided 9)
        items = [
            OCRItem(text="PASSPORT NO: P8923412", confidence=0.98, bounding_box=bbox),
            OCRItem(text="P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<", confidence=0.99, bounding_box=bbox),
            OCRItem(text="P8923412<9IND9205141M3205138<<<<<<<<<<<0<<<6", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path)
        assert res.mrz.all_check_digits_valid is False
    finally:
        if os.path.exists(path): os.remove(path)

# 10. Passport OCR / MRZ Mismatch
def test_scenario_10_passport_ocr_mrz_mismatch():
    path = create_test_image()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        # Printed VIZ says Z9999999, MRZ says P8923412
        items = [
            OCRItem(text="PASSPORT", confidence=0.99, bounding_box=bbox),
            OCRItem(text="REPUBLIC OF INDIA", confidence=0.98, bounding_box=bbox),
            OCRItem(text="PASSPORT NO: Z9999999", confidence=0.98, bounding_box=bbox),
            OCRItem(text="SURNAME: SHARMA", confidence=0.96, bounding_box=bbox),
            OCRItem(text="GIVEN NAMES: ARJUN", confidence=0.96, bounding_box=bbox),
            OCRItem(text="P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<", confidence=0.99, bounding_box=bbox),
            OCRItem(text="P8923412<8IND9205141M3205138<<<<<<<<<<<0<<<6", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path)
        assert res.mrz is not None
        assert res.mrz.overall_consistency_status == ConsistencyStatus.MISMATCH
    finally:
        if os.path.exists(path): os.remove(path)

# 11. Missing Metadata Handling
def test_scenario_11_missing_metadata():
    path = create_test_image()
    try:
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine([]))
        res = pipeline.process_document(path)
        assert res.metadata.has_exif is False
        assert res.metadata.metadata_classification == "NOT_AVAILABLE"
    finally:
        if os.path.exists(path): os.remove(path)

# 12. Missing Fields Handling
def test_scenario_12_missing_fields():
    path = create_test_image()
    try:
        # High classification score for Aadhaar, but missing document_number and name
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="GOVERNMENT OF INDIA", confidence=0.99, bounding_box=bbox),
            OCRItem(text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA", confidence=0.99, bounding_box=bbox),
            OCRItem(text="AADHAAR ENROLMENT CARD", confidence=0.99, bounding_box=bbox)
        ]
        pipeline = DocumentIntelligencePipeline(ocr_engine=MockOCREngine(items))
        res = pipeline.process_document(path)
        assert res.document_type == DocumentCategory.AADHAAR
        assert res.extracted_fields.document_number is None
        # Rule presence validation should mark as FAIL
        presence_eval = next((e for e in res.validation.evaluations if e.rule_id == "RULE_AADHAAR_PRESENCE"), None)
        assert presence_eval is not None
        assert presence_eval.status in (RuleStatus.FAIL, RuleStatus.INCONSISTENT)
    finally:
        if os.path.exists(path): os.remove(path)
