import pytest
import numpy as np
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.ocr.engine import FallbackOCREngine, PaddleOCREngine

def test_ocr_item_normalization():
    bbox = BoundingBox(x=10, y=20, width=150, height=30)
    item = OCRItem(text="GOVERNMENT OF INDIA", confidence=0.985, bounding_box=bbox, page_index=0)

    assert item.text == "GOVERNMENT OF INDIA"
    assert item.confidence == 0.985
    assert item.bounding_box.x == 10
    assert item.bounding_box.width == 150
    assert item.page_index == 0

def test_ocr_result_full_text_rebuild():
    bbox = BoundingBox(x=0, y=0, width=50, height=20)
    items = [
        OCRItem(text="PASSPORT", confidence=0.99, bounding_box=bbox),
        OCRItem(text="REPUBLIC OF INDIA", confidence=0.95, bounding_box=bbox)
    ]
    res = OCRResult(items=items)
    res.rebuild_full_text()

    assert res.full_text == "PASSPORT\nREPUBLIC OF INDIA"
    assert res.mean_confidence == 0.97

def test_empty_ocr_result():
    engine = FallbackOCREngine()
    blank_img = np.zeros((300, 300, 3), dtype=np.uint8)
    res = engine.process_image(blank_img, page_index=0)

    assert len(res.items) == 0
    assert res.full_text == ""
    assert res.mean_confidence == 0.0
    assert res.engine_name == "FallbackOCREngine"
