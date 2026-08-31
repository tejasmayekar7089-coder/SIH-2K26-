from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.common import BoundingBox

class OCRItem(BaseModel):
    """Normalized internal OCR element for a single detected text region."""
    text: str = Field(..., description="Recognized text string")
    confidence: float = Field(..., ge=0.0, le=1.0, description="OCR recognition confidence score [0.0 - 1.0]")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Bounding box (x, y, width, height)")
    page_index: int = Field(default=0, description="Zero-indexed page/image reference number")

class OCRResult(BaseModel):
    """Normalized internal OCR result for an entire document page or set of pages."""
    items: List[OCRItem] = Field(default_factory=list, description="List of recognized text items")
    full_text: str = Field(default="", description="Concatenated raw text of all items")
    mean_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mean confidence score across all items")
    engine_name: str = Field(default="PaddleOCR", description="Identifier of the OCR engine used")

    def rebuild_full_text(self) -> str:
        """Helper to re-generate concatenated full_text string."""
        lines = [item.text.strip() for item in self.items if item.text and item.text.strip()]
        self.full_text = "\n".join(lines)
        if self.items:
            self.mean_confidence = round(float(sum(item.confidence for item in self.items) / len(self.items)), 4)
        else:
            self.mean_confidence = 0.0
        return self.full_text
