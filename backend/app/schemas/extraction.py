from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox
from app.schemas.document import DocumentCategory

class ExtractedField(BaseModel):
    field_name: str
    value: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: Optional[BoundingBox] = None
    bbox: Optional[List[int]] = Field(default=None, description="[x1, y1, x2, y2] bounding box coordinates")
    source: str = Field(default="paddleocr", description="Extraction source engine e.g. paddleocr")
    provenance: str = Field(default="ocr", description="Extraction method provenance e.g. ocr:verhoeff_match")
    severity: str = Field(default="LOW", description="Field severity grade e.g. LOW, MEDIUM, HIGH")

    def model_post_init(self, __context):
        if self.bounding_box and self.bbox is None:
            self.bbox = [
                self.bounding_box.x,
                self.bounding_box.y,
                self.bounding_box.x + self.bounding_box.width,
                self.bounding_box.y + self.bounding_box.height
            ]

class ExtractionResult(BaseModel):
    document_category: DocumentCategory = DocumentCategory.UNKNOWN
    category_confidence: float = 1.0
    
    # Core VIZ Fields
    full_name: Optional[ExtractedField] = None
    date_of_birth: Optional[ExtractedField] = None
    document_number: Optional[ExtractedField] = None
    nationality: Optional[ExtractedField] = None
    gender: Optional[ExtractedField] = None
    expiry_date: Optional[ExtractedField] = None
    issue_date: Optional[ExtractedField] = None
    address: Optional[ExtractedField] = None
    
    # All raw extracted field dictionaries
    additional_fields: Dict[str, ExtractedField] = Field(default_factory=dict)
    
    # Portrait info
    has_portrait: bool = False
    portrait_bounding_box: Optional[BoundingBox] = None
    portrait_image_path: Optional[str] = None
    
    raw_text: str = ""
    ocr_confidence_mean: float = 0.0
