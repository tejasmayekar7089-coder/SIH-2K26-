import os
import tempfile
import pytest
import numpy as np
from PIL import Image

from app.schemas.document import ValidatedInputDocument, FileFormat, DocumentCategory
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.ocr.engine import BaseOCREngine
from app.modules.document_intelligence.classifier import BaseDocumentClassifier
from app.modules.document_intelligence.service import DocumentIntelligenceService

class MockOCREngine(BaseOCREngine):
    def __init__(self, mock_items):
        self.mock_items = mock_items

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        res = OCRResult(items=self.mock_items, engine_name="MockOCR")
        res.rebuild_full_text()
        return res

def create_dummy_image_file() -> str:
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "test_doc_intel_sample.png")
    img = Image.new("RGB", (600, 400), color=(240, 240, 240))
    img.save(path)
    return path

def test_extract_passport_features():
    img_path = create_dummy_image_file()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="PASSPORT", confidence=0.99, bounding_box=bbox),
            OCRItem(text="REPUBLIC OF INDIA", confidence=0.98, bounding_box=bbox),
            OCRItem(text="PASSPORT NO: P8923412", confidence=0.97, bounding_box=bbox),
            OCRItem(text="DOB: 14/05/1992", confidence=0.95, bounding_box=bbox)
        ]
        service = DocumentIntelligenceService(ocr_engine=MockOCREngine(items))

        doc_input = ValidatedInputDocument(
            document_id="DOC-TEST-001",
            file_name="passport.png",
            file_format=FileFormat.PNG,
            mime_type="image/png",
            file_size_bytes=1024,
            sha256_checksum="dummy",
            storage_path=img_path
        )

        res = service.extract_document_features(doc_input, img_path)

        assert res.document_category == DocumentCategory.PASSPORT
        assert res.category_confidence >= 0.80
        assert res.document_number is not None
        assert res.document_number.value == "P8923412"
        assert res.date_of_birth is not None
        assert res.date_of_birth.value == "14/05/1992"
        assert res.has_portrait is True
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

def test_extract_aadhaar_features():
    img_path = create_dummy_image_file()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="GOVERNMENT OF INDIA", confidence=0.99, bounding_box=bbox),
            OCRItem(text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA", confidence=0.98, bounding_box=bbox),
            OCRItem(text="DOB: 10/12/1988", confidence=0.95, bounding_box=bbox),
            OCRItem(text="MALE", confidence=0.99, bounding_box=bbox),
            OCRItem(text="9876 5432 1098", confidence=0.99, bounding_box=bbox)
        ]
        service = DocumentIntelligenceService(ocr_engine=MockOCREngine(items))

        doc_input = ValidatedInputDocument(
            document_id="DOC-TEST-002",
            file_name="aadhaar.png",
            file_format=FileFormat.PNG,
            mime_type="image/png",
            file_size_bytes=1024,
            sha256_checksum="dummy",
            storage_path=img_path
        )

        res = service.extract_document_features(doc_input, img_path)

        assert res.document_category == DocumentCategory.AADHAAR
        assert res.document_number is not None
        assert res.document_number.value == "9876 5432 1098"
        assert res.gender is not None
        assert res.gender.value == "MALE"
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

def test_extract_unsupported_document():
    img_path = create_dummy_image_file()
    try:
        bbox = BoundingBox(x=10, y=10, width=100, height=30)
        items = [
            OCRItem(text="SHOPPING INVOICE", confidence=0.99, bounding_box=bbox),
            OCRItem(text="TOTAL AMOUNT: $45.00", confidence=0.95, bounding_box=bbox)
        ]
        service = DocumentIntelligenceService(ocr_engine=MockOCREngine(items))

        doc_input = ValidatedInputDocument(
            document_id="DOC-TEST-003",
            file_name="invoice.png",
            file_format=FileFormat.PNG,
            mime_type="image/png",
            file_size_bytes=1024,
            sha256_checksum="dummy",
            storage_path=img_path
        )

        res = service.extract_document_features(doc_input, img_path)

        assert res.document_category == DocumentCategory.UNKNOWN
        assert res.category_confidence == 0.0
        assert res.document_number is None
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)
