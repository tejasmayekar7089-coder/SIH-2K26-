import pytest
from app.schemas.document import DocumentCategory
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.classifier import HeuristicDocumentClassifier

def test_classify_passport():
    classifier = HeuristicDocumentClassifier()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)
    items = [
        OCRItem(text="PASSPORT", confidence=0.99, bounding_box=bbox),
        OCRItem(text="REPUBLIC OF INDIA", confidence=0.98, bounding_box=bbox),
        OCRItem(text="P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<", confidence=0.95, bounding_box=bbox)
    ]
    ocr_res = OCRResult(items=items)
    ocr_res.rebuild_full_text()

    category, confidence = classifier.classify(ocr_res)
    assert category == DocumentCategory.PASSPORT
    assert confidence >= 0.80

def test_classify_aadhaar():
    classifier = HeuristicDocumentClassifier()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)
    items = [
        OCRItem(text="GOVERNMENT OF INDIA", confidence=0.99, bounding_box=bbox),
        OCRItem(text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA", confidence=0.98, bounding_box=bbox),
        OCRItem(text="2345 6789 0123", confidence=0.95, bounding_box=bbox)
    ]
    ocr_res = OCRResult(items=items)
    ocr_res.rebuild_full_text()

    category, confidence = classifier.classify(ocr_res)
    assert category == DocumentCategory.AADHAAR
    assert confidence >= 0.80

def test_classify_driving_licence():
    classifier = HeuristicDocumentClassifier()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)
    items = [
        OCRItem(text="UNION OF INDIA", confidence=0.99, bounding_box=bbox),
        OCRItem(text="DRIVING LICENCE", confidence=0.98, bounding_box=bbox),
        OCRItem(text="DL NO DL-1420110012345", confidence=0.95, bounding_box=bbox)
    ]
    ocr_res = OCRResult(items=items)
    ocr_res.rebuild_full_text()

    category, confidence = classifier.classify(ocr_res)
    assert category in (DocumentCategory.DRIVING_LICENSE, DocumentCategory.DRIVING_LICENCE)
    assert confidence >= 0.80

def test_classify_unknown():
    classifier = HeuristicDocumentClassifier()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)
    items = [
        OCRItem(text="GROCERY RECEIPT", confidence=0.99, bounding_box=bbox),
        OCRItem(text="MILK BREAD CHEESE", confidence=0.95, bounding_box=bbox)
    ]
    ocr_res = OCRResult(items=items)
    ocr_res.rebuild_full_text()

    category, confidence = classifier.classify(ocr_res)
    assert category == DocumentCategory.UNKNOWN
    assert confidence == 0.0
