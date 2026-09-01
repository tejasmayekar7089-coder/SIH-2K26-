import os
import cv2
import numpy as np
import pytest
from app.modules.tampering.service import TamperingAIService
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.schemas.tampering import TamperResult
from app.schemas.pipeline import DocumentProcessingResult
from app.core.config import settings

@pytest.fixture
def clean_doc_image(tmp_path):
    """Creates a clean synthetic identity document image for testing."""
    img_path = str(tmp_path / "clean_test_doc.jpg")
    img = np.ones((500, 800, 3), dtype=np.uint8) * 245
    cv2.rectangle(img, (20, 20), (780, 480), (40, 40, 40), 2)
    cv2.putText(img, "SPECIMEN PASSPORT", (250, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 100), 2)
    cv2.putText(img, "P<INDTEST<<SAMPLE<<<<<<<<<<<<<<<<<<<<<<<<<<<", (40, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 1)
    cv2.putText(img, "A1234567890IND9008151M3008155<<<<<<<<<<<<<<02", (40, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 1)
    cv2.imwrite(img_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return img_path

@pytest.fixture
def tampered_doc_image(tmp_path):
    """Creates a synthetically manipulated document image (edited text patch)."""
    img_path = str(tmp_path / "tampered_test_doc.jpg")
    img = np.ones((500, 800, 3), dtype=np.uint8) * 245
    cv2.rectangle(img, (20, 20), (780, 480), (40, 40, 40), 2)
    cv2.putText(img, "SPECIMEN PASSPORT", (250, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 20, 100), 2)
    
    # Insert high-contrast noise patch simulating pasted text/date change
    cv2.rectangle(img, (220, 200), (450, 240), (255, 255, 255), -1)
    cv2.putText(img, "15/08/1998", (230, 230), cv2.FONT_HERSHEY_DUPLEX, 0.8, (0, 0, 0), 3)
    
    # Save at lower quality to introduce local compression mismatch
    cv2.imwrite(img_path, img, [cv2.IMWRITE_JPEG_QUALITY, 75])
    return img_path

def test_tampering_service_clean_image(clean_doc_image):
    service = TamperingAIService()
    res = service.analyze_tampering(image_input=clean_doc_image)
    
    assert isinstance(res, TamperResult)
    assert res.heatmap_available is True
    assert res.processing_time_ms >= 0
    assert os.path.exists(res.heatmap_image_path)
    assert os.path.exists(res.mask_image_path)

def test_tampering_service_manipulated_image(tampered_doc_image):
    service = TamperingAIService()
    res = service.analyze_tampering(image_input=tampered_doc_image)
    
    assert isinstance(res, TamperResult)
    assert res.tampering_detected is True
    assert res.risk_level in ["MEDIUM", "HIGH"]
    assert res.confidence >= 0.35
    assert len(res.suspicious_regions) > 0

def test_pipeline_integration_with_tampering(clean_doc_image):
    pipeline = DocumentIntelligencePipeline()
    res = pipeline.process_document(clean_doc_image, document_id="DOC-TEST-INTEG")
    
    assert isinstance(res, DocumentProcessingResult)
    assert res.tampering is not None
    assert isinstance(res.tampering, TamperResult)
    assert res.tampering.model == "SIGNAL_MULTI_STREAM_ELA_SRM"
    assert res.ocr is not None
    assert res.extracted_fields is not None
    assert res.validation is not None
