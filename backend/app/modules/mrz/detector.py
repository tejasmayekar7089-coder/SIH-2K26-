import re
from typing import List, Tuple, Optional
import numpy as np
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRResult, OCRItem
from app.core.logging import get_logger

logger = get_logger("mrz_detector")

class MRZDetector:
    """Detects and isolates TD3 MRZ lines from OCR results or image bounding boxes."""

    MRZ_LINE1_RE = re.compile(r'P[A-Z0-9<]{43}')
    MRZ_LINE2_RE = re.compile(r'[A-Z0-9<]{44}')
    MRZ_LOOSE_RE = re.compile(r'[A-Z0-9<]{30,44}')

    def detect_mrz(self, ocr_result: OCRResult) -> Tuple[List[str], Optional[BoundingBox]]:
        """
        Detects TD3 MRZ lines from OCR items.
        Returns (raw_mrz_lines, combined_bounding_box).
        """
        if not ocr_result or not ocr_result.items:
            return [], None

        found_lines: List[Tuple[int, str, Optional[BoundingBox]]] = []

        # 1. Clean OCR items and check for MRZ patterns
        for idx, item in enumerate(ocr_result.items):
            cleaned_text = re.sub(r'\s+', '', item.text.upper())
            # Replace common OCR misreads in MRZ text (e.g. spaces, « to <)
            cleaned_text = cleaned_text.replace("«", "<").replace("<<", "<")

            if self.MRZ_LINE1_RE.search(cleaned_text):
                found_lines.append((idx, self.MRZ_LINE1_RE.search(cleaned_text).group(0), item.bounding_box))
            elif self.MRZ_LINE2_RE.search(cleaned_text):
                found_lines.append((idx, self.MRZ_LINE2_RE.search(cleaned_text).group(0), item.bounding_box))

        if len(found_lines) >= 2:
            # Sort by Y position or item index
            found_lines.sort(key=lambda x: x[0])
            raw_lines = [line[1] for line in found_lines[:2]]
            bbox = self._merge_bounding_boxes([line[2] for line in found_lines[:2] if line[2]])
            logger.info(f"MRZDetector found {len(raw_lines)} TD3 MRZ lines via OCR pattern match.")
            return raw_lines, bbox

        # 2. Fallback heuristic: search bottom 30% of items for MRZ character sequences
        bottom_items = [
            it for it in ocr_result.items
            if self.MRZ_LOOSE_RE.search(it.text.replace(" ", ""))
        ]

        if len(bottom_items) >= 2:
            raw_lines = [re.sub(r'\s+', '', it.text.upper()) for it in bottom_items[:2]]
            # Pad or trim to 44 chars if needed
            raw_lines = [line[:44].ljust(44, '<') for line in raw_lines]
            bbox = self._merge_bounding_boxes([it.bounding_box for it in bottom_items[:2] if it.bounding_box])
            logger.info("MRZDetector found MRZ lines via fallback bottom-cluster heuristic.")
            return raw_lines, bbox

        logger.info("MRZDetector: No valid MRZ lines detected.")
        return [], None

    def _merge_bounding_boxes(self, bboxes: List[BoundingBox]) -> Optional[BoundingBox]:
        if not bboxes:
            return None
        xs = [b.x for b in bboxes]
        ys = [b.y for b in bboxes]
        x2s = [b.x + b.width for b in bboxes]
        y2s = [b.y + b.height for b in bboxes]
        return BoundingBox(
            x=min(xs),
            y=min(ys),
            width=max(x2s) - min(xs),
            height=max(y2s) - min(ys)
        )
