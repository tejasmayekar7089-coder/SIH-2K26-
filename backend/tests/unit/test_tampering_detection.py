import os

import cv2
import numpy as np

from app.modules.tampering.service import TamperingAIService
from app.schemas.document import ValidatedInputDocument, FileFormat


def test_tampering_detector_flags_edge_anomaly_with_bbox():
    service = TamperingAIService()

    image = np.full((400, 400, 3), 230, dtype=np.uint8)
    cv2.rectangle(image, (80, 80), (220, 220), (180, 180, 180), -1)

    tamper_patch = np.full((120, 120, 3), 60, dtype=np.uint8)
    cv2.rectangle(tamper_patch, (20, 20), (100, 90), (20, 20, 20), -1)
    image[150:270, 150:270] = tamper_patch

    tamper_score, mask, regions = service._execute_doctamper(image)
    structured = {
        "tamper_score": tamper_score,
        "status": "TAMPERED" if tamper_score >= 0.45 else "CLEAR",
        "severity": "HIGH" if tamper_score >= 0.75 else "MEDIUM" if tamper_score >= 0.45 else "LOW",
        "confidence": tamper_score,
        "regions": regions,
    }

    assert structured["tamper_score"] >= 0.0
    assert mask.shape == image.shape[:2]
    assert len(structured["regions"]) >= 1
    assert all(region.bounding_box.width > 0 and region.bounding_box.height > 0 for region in structured["regions"])
    assert structured["status"] in {"TAMPERED", "CLEAR"}
    assert structured["severity"] in {"LOW", "MEDIUM", "HIGH"}
    assert 0.0 <= structured["confidence"] <= 1.0


def test_analyze_tampering_saves_visualized_bbox_output(tmp_path):
    service = TamperingAIService()
    image = np.full((300, 300, 3), 230, dtype=np.uint8)
    cv2.rectangle(image, (60, 60), (180, 170), (190, 190, 190), -1)
    cv2.rectangle(image, (120, 120), (240, 220), (60, 60, 60), -1)

    input_path = tmp_path / "tamper_sample.png"
    cv2.imwrite(str(input_path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))

    doc = ValidatedInputDocument(
        document_id="doc-visualize-1",
        file_name="tamper_sample.png",
        file_format=FileFormat.PNG,
        mime_type="image/png",
        file_size_bytes=input_path.stat().st_size,
        sha256_checksum="abc123",
        storage_path=str(input_path),
    )

    result = service.analyze_tampering(doc, str(input_path))

    assert os.path.exists(result.heatmap_image_path)
    annotated = cv2.imread(result.heatmap_image_path)
    assert annotated is not None
    assert annotated.size > 0
    assert len(result.regions) >= 1
