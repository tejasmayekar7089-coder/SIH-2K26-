from typing import List, Dict, Optional
import numpy as np
from app.schemas.extraction import ExtractionResult
from app.schemas.tampering import TamperResult
from app.schemas.field_mapping import FieldMappingResult, FieldTamperOverlap
from app.schemas.common import SeverityLevel, BoundingBox
from app.core.logging import get_logger

logger = get_logger("field_mapping")

class FieldMappingService:
    def __init__(self):
        pass

    def map_tamper_to_fields(
        self,
        extraction: ExtractionResult,
        tamper_result: TamperResult
    ) -> FieldMappingResult:
        """Module 7: Field-Evidence Spatial Overlap Mapping."""
        logger.info("Mapping tampering mask to extracted document fields")
        
        overlaps: List[FieldTamperOverlap] = []
        
        # Candidate fields to inspect
        fields_to_check = [
            ("Full Name", extraction.full_name),
            ("Date of Birth", extraction.date_of_birth),
            ("Document Number", extraction.document_number),
            ("Expiry Date", extraction.expiry_date),
            ("Nationality", extraction.nationality),
        ]
        
        has_tampered_fields = False
        highest_severity = SeverityLevel.LOW
        highest_field = None

        # If mask exists, calculate intersection ratio
        mask = None
        if tamper_result.mask_image_path:
            try:
                import cv2
                raw_mask = cv2.imread(tamper_result.mask_image_path, cv2.IMREAD_GRAYSCALE)
                if raw_mask is not None:
                    mask = raw_mask > 128
            except ImportError:
                from PIL import Image
                with Image.open(tamper_result.mask_image_path) as mask_img:
                    mask = np.array(mask_img.convert('L')) > 128

        for field_name, field_obj in fields_to_check:
            if not field_obj or not field_obj.bounding_box:
                continue
            
            bbox = field_obj.bounding_box
            overlap_ratio = 0.0
            
            if mask is not None:
                bx1, by1 = max(0, bbox.x), max(0, bbox.y)
                bx2, by2 = min(mask.shape[1], bbox.x + bbox.width), min(mask.shape[0], bbox.y + bbox.height)
                
                if bx2 > bx1 and by2 > by1:
                    field_roi = mask[by1:by2, bx1:bx2]
                    overlap_pixels = np.sum(field_roi)
                    total_box_pixels = (bx2 - bx1) * (by2 - by1)
                    overlap_ratio = float(overlap_pixels / total_box_pixels) if total_box_pixels > 0 else 0.0

            # Determine risk tier based on overlap
            if overlap_ratio >= 0.35:
                risk = SeverityLevel.HIGH
                reason_code = f"TAMPER_OVERLAP_{field_name.upper().replace(' ', '_')}"
                has_tampered_fields = True
                highest_severity = SeverityLevel.HIGH
                highest_field = field_name
            elif overlap_ratio >= 0.15:
                risk = SeverityLevel.MEDIUM
                reason_code = f"SUSPECT_OVERLAP_{field_name.upper().replace(' ', '_')}"
                if highest_severity != SeverityLevel.HIGH:
                    highest_severity = SeverityLevel.MEDIUM
                    highest_field = field_name
            else:
                risk = SeverityLevel.LOW
                reason_code = None

            overlaps.append(FieldTamperOverlap(
                field_name=field_name,
                extracted_text=field_obj.value,
                overlap_ratio=round(overlap_ratio, 3),
                tamper_risk=risk,
                reason_code=reason_code
            ))

        return FieldMappingResult(
            field_overlaps=overlaps,
            has_tampered_fields=has_tampered_fields,
            highest_risk_field=highest_field,
            highest_severity=highest_severity
        )
