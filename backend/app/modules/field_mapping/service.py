from typing import List, Dict, Any
import logging
from app.schemas.extraction import ExtractionResult

logger = logging.getLogger("field_mapping")

def map_tampering_to_fields(tamper_regions: List[List[int]], extraction: ExtractionResult) -> List[Dict[str, str]]:
    """
    Map suspicious tampering regions to OCR fields to assess risk per field.
    Returns a list of fields with their associated risk level.
    """
    logger.info("Mapping tampering mask to extracted document fields")
    field_mapping_result = []
    
    # Extract fields from extraction result
    fields_to_check = {
        "Full Name": extraction.full_name,
        "Date of Birth": extraction.date_of_birth,
        "Document Number": extraction.document_number,
        "Nationality": extraction.nationality,
        "Gender": extraction.gender,
        "Expiry Date": extraction.expiry_date,
        "Issue Date": extraction.issue_date,
        "Address": extraction.address
    }
    
    for field_name, field_obj in fields_to_check.items():
        if not field_obj or not field_obj.bbox:
            continue
            
        bx1, by1, bx2, by2 = field_obj.bbox
        
        risk = "LOW"
        for region in tamper_regions:
            rx1, ry1, rx2, ry2 = region
            
            # Check overlap
            ox1 = max(bx1, rx1)
            oy1 = max(by1, ry1)
            ox2 = min(bx2, rx2)
            oy2 = min(by2, ry2)
            
            if ox2 > ox1 and oy2 > oy1:
                risk = "HIGH"
                break
                
        field_mapping_result.append({"field": field_name, "risk": risk})
        
    # Check portrait
    if extraction.portrait_bounding_box:
        p_bbox = extraction.portrait_bounding_box
        bx1, by1, bx2, by2 = p_bbox.x, p_bbox.y, p_bbox.x + p_bbox.width, p_bbox.y + p_bbox.height
        risk = "LOW"
        for region in tamper_regions:
            rx1, ry1, rx2, ry2 = region
            ox1 = max(bx1, rx1)
            oy1 = max(by1, ry1)
            ox2 = min(bx2, rx2)
            oy2 = min(by2, ry2)
            if ox2 > ox1 and oy2 > oy1:
                risk = "HIGH"
                break
        field_mapping_result.append({"field": "Photo", "risk": risk})
        
    logger.info(f"Field mapping result: {field_mapping_result}")
    return field_mapping_result
