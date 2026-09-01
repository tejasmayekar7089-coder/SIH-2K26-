import re
from typing import List, Tuple, Optional
import numpy as np
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRResult, OCRItem
from app.core.logging import get_logger

logger = get_logger("mrz_detector")

class MRZDetector:
    """Detects and isolates TD3 MRZ lines from OCR results or image bounding boxes."""

    MRZ_LINE1_RE = re.compile(r'P[A-Z0-9<]{40,43}')
    MRZ_LINE2_RE = re.compile(r'[A-Z0-9<]{40,44}')
    MRZ_LOOSE_RE = re.compile(r'[A-Z0-9<]{30,44}')

    def detect_mrz(self, ocr_result: OCRResult) -> Tuple[List[str], Optional[BoundingBox]]:
        """
        Detects TD3 MRZ lines from OCR items.
        Returns (raw_mrz_lines, combined_bounding_box).
        """
        if not ocr_result or not ocr_result.items:
            return [], None

        found_lines: List[Tuple[int, float, str, Optional[BoundingBox]]] = []

        # 1. Clean OCR items and check for MRZ patterns
        for idx, item in enumerate(ocr_result.items):
            raw_text = item.text.upper().strip()
            # Replace spaces and common OCR misreads in MRZ text
            cleaned_text = re.sub(r'\s+', '', raw_text)
            cleaned_text = cleaned_text.replace("«", "<").replace("{", "<").replace("}", "<").replace("(", "<").replace(")", "<")
            # Replace common OCR misreads in MRZ prefix if needed
            if cleaned_text.startswith("P(") or cleaned_text.startswith("P[") or cleaned_text.startswith("P{"):
                cleaned_text = "P<" + cleaned_text[2:]

            y_pos = item.bounding_box.y if item.bounding_box else float(idx)

            # Check for TD3 Line 1 (starts with P and contains fillers <)
            if cleaned_text.startswith("P<") or cleaned_text.startswith("P") and "<" in cleaned_text:
                if len(cleaned_text) >= 30:
                    # Pad to 44 chars if needed
                    padded = cleaned_text[:44].ljust(44, '<')
                    found_lines.append((idx, y_pos, padded, item.bounding_box))
                    continue

            # Check for TD3 Line 2 (Passport number + checksums + dates)
            if len(cleaned_text) >= 30 and "<" in cleaned_text and not cleaned_text.startswith("P<"):
                # Must contain numbers and fillers
                num_digits = sum(c.isdigit() for c in cleaned_text)
                if num_digits >= 6:
                    padded = cleaned_text[:44].ljust(44, '<')
                    found_lines.append((idx, y_pos, padded, item.bounding_box))

        if len(found_lines) >= 2:
            # Sort by Y position to ensure Line 1 (top) is before Line 2 (bottom)
            found_lines.sort(key=lambda x: (x[1], x[0]))
            line1 = found_lines[0][2]
            line2 = found_lines[1][2]
            
            # Ensure line1 starts with P< if line2 does not
            if not line1.startswith("P") and line2.startswith("P"):
                line1, line2 = line2, line1

            raw_lines = [line1, line2]
            bboxes = [f[3] for f in found_lines[:2] if f[3] is not None]
            bbox = self._merge_bounding_boxes(bboxes)
            logger.info(f"[MRZ] MRZDetector found 2 TD3 MRZ lines via OCR pattern match: Line1={line1[:15]}..., Line2={line2[:15]}...")
            return raw_lines, bbox

        # 2. Fallback heuristic: search bottom items for MRZ character sequences
        bottom_items = [
            it for it in ocr_result.items
            if self.MRZ_LOOSE_RE.search(re.sub(r'\s+', '', it.text.upper()).replace("«", "<"))
        ]

        if len(bottom_items) >= 2:
            raw_lines = [re.sub(r'\s+', '', it.text.upper()).replace("«", "<") for it in bottom_items[:2]]
            raw_lines = [line[:44].ljust(44, '<') for line in raw_lines]
            bboxes = [it.bounding_box for it in bottom_items[:2] if it.bounding_box]
            bbox = self._merge_bounding_boxes(bboxes)
            logger.info(f"[MRZ] MRZDetector found MRZ lines via fallback heuristic.")
            return raw_lines, bbox

        logger.info("[MRZ] MRZDetector: No valid MRZ lines detected.")
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

