import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from app.schemas.common import BoundingBox
from app.schemas.tampering import SuspiciousRegion
from app.schemas.extraction import ExtractionResult
from app.modules.document_intelligence.ocr.schemas import OCRResult, OCRItem
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("tampering_localization")

class TamperingLocalizer:
    """Extracts suspicious anomaly bounding boxes and correlates them with OCR text/photo regions."""

    @classmethod
    def extract_suspicious_regions(cls, fused_map: np.ndarray, threshold_scale: float = 2.5) -> Tuple[List[SuspiciousRegion], np.ndarray]:
        """
        Thresholds fused anomaly map to extract candidate bounding boxes and binary mask.
        Returns list of SuspiciousRegion Pydantic models and 2D binary mask.
        """
        h, w = fused_map.shape[:2]
        mean_val, std_val = cv2.meanStdDev(fused_map)
        cutoff = mean_val[0][0] + (threshold_scale * std_val[0][0])
        cutoff_int = min(240, max(30, int(cutoff)))

        _, binary_mask = cv2.threshold(fused_map, cutoff_int, 255, cv2.THRESH_BINARY)

        # Morphology cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        binary_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(binary_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        suspicious_regions: List[SuspiciousRegion] = []
        min_area = settings.TAMPER_CONTOUR_MIN_AREA

        reg_idx = 1
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area:
                x, y, bw, bh = cv2.boundingRect(cnt)
                
                # Calculate mean anomaly intensity inside contour
                roi = fused_map[y:y+bh, x:x+bw]
                mean_intensity = float(np.mean(roi)) if roi.size > 0 else 128.0
                anomaly_score = min(1.0, round(mean_intensity / 255.0 * 1.5, 2))

                bbox = BoundingBox(x=x, y=y, width=bw, height=bh)
                
                # Initial heuristic anomaly type
                anomaly_type = cls._infer_region_type(bbox, h, w)

                suspicious_regions.append(SuspiciousRegion(
                    region_id=f"REG-{reg_idx:02d}",
                    bounding_box=bbox,
                    anomaly_score=anomaly_score,
                    anomaly_type=anomaly_type
                ))
                reg_idx += 1

        return suspicious_regions, binary_mask

    @classmethod
    def correlate_with_ocr(
        cls,
        suspicious_regions: List[SuspiciousRegion],
        ocr_result: Optional[OCRResult],
        extraction: Optional[ExtractionResult],
        image_shape: Tuple[int, int]
    ) -> List[Dict[str, any]]:
        """
        Correlates detected tampering bounding boxes with OCR field bounding boxes.
        Returns list of spatial overlap evidence items explaining affected document fields.
        """
        correlations = []
        h, w = image_shape[:2]

        if not suspicious_regions:
            return correlations

        # Map extracted field names to their values for contextual explanations
        extracted_fields_map = {}
        if extraction:
            for field_name in ["full_name", "date_of_birth", "document_number", "expiry_date", "nationality", "gender"]:
                field_obj = getattr(extraction, field_name, None)
                if field_obj and hasattr(field_obj, "value") and field_obj.value:
                    extracted_fields_map[field_name] = field_obj.value

        # Check OCR item overlaps
        ocr_items = ocr_result.items if ocr_result else []

        for reg in suspicious_regions:
            reg_box = reg.bounding_box
            
            # Check overlap with portrait photo region (typically left quadrant for Passports/IDs)
            if cls._is_photo_region(reg_box, h, w):
                reg.anomaly_type = "PHOTO_REPLACEMENT"
                correlations.append({
                    "region_id": reg.region_id,
                    "field_name": "portrait_photo",
                    "field_label": "Holder Photograph",
                    "anomaly_type": "PHOTO_REPLACEMENT",
                    "overlap_ratio": 0.85,
                    "description": "Image inconsistency detected around holder photograph region"
                })
                continue

            # Check overlap with OCR text boxes
            matched_ocr_text = []
            for item in ocr_items:
                if not item.bounding_box:
                    continue
                ocr_box = item.bounding_box
                overlap = cls._calculate_iou(reg_box, ocr_box)
                if overlap > 0.05:
                    matched_ocr_text.append((item.text, overlap))

            if matched_ocr_text:
                matched_ocr_text.sort(key=lambda t: t[1], reverse=True)
                primary_text = matched_ocr_text[0][0]
                
                # Check if text matches known extracted identity fields
                matched_field_name = cls._match_text_to_extracted_field(primary_text, extracted_fields_map)
                
                if matched_field_name:
                    reg.anomaly_type = "TEXT_MANIPULATION"
                    correlations.append({
                        "region_id": reg.region_id,
                        "field_name": matched_field_name,
                        "field_label": matched_field_name.replace("_", " ").title(),
                        "anomaly_type": "TEXT_MANIPULATION",
                        "overlap_ratio": round(matched_ocr_text[0][1], 2),
                        "description": f"Suspicious manipulation detected around {matched_field_name.replace('_', ' ').title()} field ('{primary_text}')"
                    })
                else:
                    reg.anomaly_type = "COPY_PASTE" if len(matched_ocr_text) > 1 else "TEXT_MANIPULATION"
                    correlations.append({
                        "region_id": reg.region_id,
                        "field_name": "ocr_text_region",
                        "field_label": "Document Text Region",
                        "anomaly_type": reg.anomaly_type,
                        "overlap_ratio": round(matched_ocr_text[0][1], 2),
                        "description": f"Tampering heatmap overlaps OCR text region ('{primary_text}')"
                    })

        return correlations

    @staticmethod
    def _calculate_iou(box1: BoundingBox, box2: BoundingBox) -> float:
        """Calculates Intersection over Union (IoU) between two bounding boxes."""
        b1_x1, b1_y1, b1_x2, b1_y2 = box1.x, box1.y, box1.x + box1.width, box1.y + box1.height
        b2_x1, b2_y1, b2_x2, b2_y2 = box2.x, box2.y, box2.x + box2.width, box2.y + box2.height

        x_left = max(b1_x1, b2_x1)
        y_top = max(b1_y1, b2_y1)
        x_right = min(b1_x2, b2_x2)
        y_bottom = min(b1_y2, b2_y2)

        if x_right < x_left or y_bottom < y_top:
            return 0.0

        intersection_area = (x_right - x_left) * (y_bottom - y_top)
        box1_area = box1.width * box1.height
        box2_area = box2.width * box2.height

        union_area = float(box1_area + box2_area - intersection_area)
        if union_area <= 0:
            return 0.0
        return intersection_area / union_area

    @staticmethod
    def _is_photo_region(box: BoundingBox, h: int, w: int) -> bool:
        """Heuristic check whether bounding box overlaps holder portrait zone."""
        center_x = box.x + (box.width / 2.0)
        center_y = box.y + (box.height / 2.0)
        
        is_left_photo = (center_x / w < 0.35) and (0.2 < center_y / h < 0.75)
        is_right_photo = (center_x / w > 0.65) and (0.2 < center_y / h < 0.75)
        box_area_ratio = (box.width * box.height) / float(h * w)

        return (is_left_photo or is_right_photo) and (box_area_ratio > 0.04)

    @staticmethod
    def _infer_region_type(box: BoundingBox, h: int, w: int) -> str:
        """Infers initial anomaly category based on aspect ratio and size."""
        aspect = box.width / float(box.height) if box.height > 0 else 1.0

        if aspect > 3.0:
            return "TEXT_MANIPULATION" # Wide text line edit
        elif 0.7 <= aspect <= 1.4 and (box.width * box.height) > (0.05 * h * w):
            return "PHOTO_REPLACEMENT" # Square/portrait patch
        else:
            return "COPY_PASTE"

    @staticmethod
    def _match_text_to_extracted_field(ocr_text: str, fields_map: Dict[str, str]) -> Optional[str]:
        """Matches OCR text snippet to extracted identity document fields."""
        clean_ocr = ocr_text.upper().strip()
        if len(clean_ocr) < 2:
            return None

        for fname, fval in fields_map.items():
            if not fval:
                continue
            clean_fval = str(fval).upper().strip()
            if clean_ocr in clean_fval or clean_fval in clean_ocr:
                return fname
        return None
