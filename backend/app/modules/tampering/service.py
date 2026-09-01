import os
import time
import cv2
import numpy as np
from typing import Optional, List, Tuple, Any

from app.schemas.document import ValidatedInputDocument
from app.schemas.tampering import TamperResult, TamperModelSource, SuspiciousRegion
from app.schemas.extraction import ExtractionResult
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.core.config import settings
from app.core.logging import get_logger
from app.utils.image_utils import load_image_rgb, save_image_rgb, generate_heatmap_overlay

from app.modules.tampering.preprocessing import TamperingPreprocessor
from app.modules.tampering.localization import TamperingLocalizer
from app.modules.tampering.scoring import TamperingScorer
from app.modules.tampering.evidence import TamperingEvidenceBuilder

logger = get_logger("tampering_ai")

class TamperingAIService:
    """
    Unified Modular Tampering AI Analysis Service.
    Integrates Multi-Stream ELA + High-Pass Noise Variance, OCR field correlation,
    heatmap visualization, dynamic confidence scoring, and evidence generation.
    """

    def __init__(self):
        self.model_name = "SIGNAL_MULTI_STREAM_ELA_SRM"

    def analyze_tampering(
        self,
        doc: Optional[ValidatedInputDocument] = None,
        image_input: Optional[Any] = None,
        ocr_result: Optional[OCRResult] = None,
        extraction: Optional[ExtractionResult] = None
    ) -> TamperResult:
        """
        Executes end-to-end multi-stage tampering analysis.
        Parameters:
            - doc: ValidatedInputDocument or None
            - image_input: File path (str) or RGB numpy image array
            - ocr_result: OCRResult (optional for OCR text field correlation)
            - extraction: ExtractionResult (optional for extracted field correlation)
        """
        t0 = time.time()
        doc_id = doc.document_id if doc else "DOC-TEMP"
        logger.info(f"Executing modular Tampering AI pipeline for document: {doc_id}")

        # 1. Load image RGB array
        image_rgb = None
        if isinstance(image_input, np.ndarray):
            image_rgb = image_input
        elif isinstance(image_input, str) and os.path.exists(image_input):
            image_rgb = load_image_rgb(image_input)
        elif doc and hasattr(doc, "storage_path") and os.path.exists(doc.storage_path):
            image_rgb = load_image_rgb(doc.storage_path)

        if image_rgb is None or image_rgb.size == 0:
            logger.warning(f"Invalid or empty image payload for tampering analysis on {doc_id}")
            return TamperResult(
                model_used=TamperModelSource.SIGNAL_MULTI_STREAM_ELA_SRM,
                model=self.model_name,
                is_tampered=False,
                tampering_detected=False,
                confidence=0.0,
                tamper_score=0.0,
                risk_level="LOW",
                heatmap_available=False,
                processing_time_ms=int((time.time() - t0) * 1000)
            )

        h, w = image_rgb.shape[:2]

        # 2. Stage A: Multi-Stream Preprocessing (ELA + SRM Noise Map)
        ela_map = TamperingPreprocessor.compute_ela_diff(image_rgb)
        srm_map = TamperingPreprocessor.compute_srm_noise_map(image_rgb)
        fused_map = TamperingPreprocessor.fuse_anomaly_maps(ela_map, srm_map)

        # 3. Stage B: Localization & Anomaly Bounding Box Extraction
        suspicious_regions, binary_mask = TamperingLocalizer.extract_suspicious_regions(fused_map)

        # 4. Stage C: Spatial OCR Field Correlation
        correlations = TamperingLocalizer.correlate_with_ocr(
            suspicious_regions=suspicious_regions,
            ocr_result=ocr_result,
            extraction=extraction,
            image_shape=(h, w)
        )

        # 5. Stage D: Scoring & Risk Determination
        confidence, tampering_detected, risk_level, tampering_types = TamperingScorer.evaluate(
            fused_map=fused_map,
            suspicious_regions=suspicious_regions,
            correlations=correlations
        )

        # 6. Stage E: Evidence Generation
        evidence_items, explainable_reasons = TamperingEvidenceBuilder.build_evidence(
            confidence=confidence,
            risk_level=risk_level,
            tampering_detected=tampering_detected,
            suspicious_regions=suspicious_regions,
            correlations=correlations,
            model_name=self.model_name
        )

        # 7. Render Heatmap Overlay & Mask Images
        heatmap_overlay = generate_heatmap_overlay(image_rgb, fused_map.astype(np.float32) / 255.0, alpha=0.45)
        
        # Draw bounding boxes on heatmap overlay for visual review
        for reg in suspicious_regions:
            bx = reg.bounding_box
            color = (255, 0, 0) if risk_level == "HIGH" else (255, 165, 0)
            x2 = bx.x + bx.width
            y2 = bx.y + bx.height
            cv2.rectangle(heatmap_overlay, (bx.x, bx.y), (x2, y2), color, 2)
            cv2.putText(
                heatmap_overlay,
                f"{reg.region_id} ({reg.anomaly_type})",
                (bx.x, max(15, bx.y - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1
            )

        heatmap_path = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_tamper_heatmap.jpg")
        mask_path = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_tamper_mask.png")

        save_image_rgb(heatmap_overlay, heatmap_path)
        cv2.imwrite(mask_path, binary_mask)

        t1 = time.time()
        elapsed_ms = int((t1 - t0) * 1000)

        logger.info(
            f"[TAMPERING AI] Complete for {doc_id}: detected={tampering_detected}, "
            f"confidence={confidence:.2f}, risk={risk_level}, regions={len(suspicious_regions)}, time={elapsed_ms}ms"
        )

        return TamperResult(
            model_used=TamperModelSource.SIGNAL_MULTI_STREAM_ELA_SRM,
            model=self.model_name,
            is_tampered=tampering_detected,
            tampering_detected=tampering_detected,
            confidence=confidence,
            tamper_score=confidence,
            risk_level=risk_level,
            tampering_types=tampering_types,
            heatmap_available=True,
            heatmap_image_path=heatmap_path,
            mask_image_path=mask_path,
            suspicious_regions=suspicious_regions,
            evidence=evidence_items,
            processing_time_ms=elapsed_ms,
            fallback_invoked=False,
            fallback_reason=None
        )
