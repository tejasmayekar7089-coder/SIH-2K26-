import os
import numpy as np
from typing import Optional, Dict, Tuple, List, Any

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from app.schemas.document import ValidatedInputDocument, DocumentCategory
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.common import BoundingBox
from app.modules.acquisition.loader import DocumentLoader
from app.modules.document_intelligence.ocr.engine import BaseOCREngine, PaddleOCREngine
from app.modules.document_intelligence.classifier import BaseDocumentClassifier, HeuristicDocumentClassifier
from app.modules.document_intelligence.extractors.base import BaseFieldExtractor
from app.modules.document_intelligence.extractors.aadhaar import AadhaarFieldExtractor
from app.modules.document_intelligence.extractors.driving_licence import DrivingLicenceFieldExtractor
from app.modules.document_intelligence.extractors.passport import PassportFieldExtractor
from app.utils.image_utils import load_image_rgb, save_image_rgb
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("document_intelligence")

class DocumentIntelligenceService:
    """Module 3: Document Layout, OCR, Heuristic Classification & Field Extraction."""

    def __init__(self,
                 ocr_engine: BaseOCREngine = None,
                 classifier: BaseDocumentClassifier = None):
        self.ocr_engine = ocr_engine or PaddleOCREngine()
        self.classifier = classifier or HeuristicDocumentClassifier()
        self.extractors: Dict[DocumentCategory, BaseFieldExtractor] = {
            DocumentCategory.AADHAAR: AadhaarFieldExtractor(),
            DocumentCategory.DRIVING_LICENSE: DrivingLicenceFieldExtractor(),
            DocumentCategory.DRIVING_LICENCE: DrivingLicenceFieldExtractor(),
            DocumentCategory.PASSPORT: PassportFieldExtractor()
        }

    def extract_document_features(self, doc: ValidatedInputDocument, image_path: str) -> ExtractionResult:
        """Runs genuine OCR, classification, portrait extraction, and field parsing."""
        logger.info(f"Extracting document intelligence for doc {doc.document_id} from {image_path}")

        # 1. Load image safely
        try:
            image_rgb = DocumentLoader.load_single_page_rgb(image_path)
        except Exception as e:
            logger.error(f"Failed to load image for doc {doc.document_id}: {e}")
            return ExtractionResult(
                document_category=DocumentCategory.UNKNOWN,
                category_confidence=0.0,
                raw_text="",
                ocr_confidence_mean=0.0
            )

        h, w = image_rgb.shape[:2]

        # 2. Perform OCR Engine Extraction
        ocr_result = self.ocr_engine.process_image(image_rgb, page_index=0)
        logger.info(f"OCR finished for {doc.document_id}: found {len(ocr_result.items)} text items")

        # 3. Classify Document Type
        doc_category, cat_confidence = self.classifier.classify(ocr_result, image_rgb)

        # 4. Extract Category-Specific Fields
        extractor = self.extractors.get(doc_category)
        if extractor:
            extraction_result = extractor.extract_fields(ocr_result)
            extraction_result.document_category = doc_category
            extraction_result.category_confidence = cat_confidence
        else:
            # UNKNOWN or Unsupported category
            extraction_result = ExtractionResult(
                document_category=doc_category,
                category_confidence=cat_confidence,
                raw_text=ocr_result.full_text,
                ocr_confidence_mean=ocr_result.mean_confidence
            )

        # 5. Extract Portrait Photo Crop if present
        portrait_path, portrait_box, has_portrait = self._extract_portrait_photo(doc.document_id, image_rgb)
        extraction_result.has_portrait = has_portrait
        extraction_result.portrait_bounding_box = portrait_box
        extraction_result.portrait_image_path = portrait_path

        return extraction_result

    def _extract_portrait_photo(self, doc_id: str, image_rgb: np.ndarray) -> Tuple[Optional[str], Optional[BoundingBox], bool]:
        """Detect and crop portrait photo anchor from document image."""
        h, w = image_rgb.shape[:2]
        if h < 50 or w < 50:
            return None, None, False

        # Attempt OpenCV Face detection heuristic
        if HAS_CV2:
            try:
                gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
                cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
                if os.path.exists(cascade_path):
                    face_cascade = cv2.CascadeClassifier(cascade_path)
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(30, 30))
                    if len(faces) > 0:
                        fx, fy, fw, fh = faces[0]
                        # Expand face bounding box to include full head/shoulders portrait
                        px1 = max(0, int(fx - 0.2 * fw))
                        py1 = max(0, int(fy - 0.3 * fh))
                        px2 = min(w, int(fx + 1.2 * fw))
                        py2 = min(h, int(fy + 1.4 * fh))
                        portrait_crop = image_rgb[py1:py2, px1:px2]

                        if portrait_crop.size > 0:
                            out_path = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_portrait.jpg")
                            save_image_rgb(portrait_crop, out_path)
                            bbox = BoundingBox(x=px1, y=py1, width=px2 - px1, height=py2 - py1)
                            return out_path, bbox, True
            except Exception as e:
                logger.warning(f"Face cascade detection failed: {e}")

        # Standard ID Photo position heuristic (approx left 5-40% width, top 20-75% height)
        px1, py1, px2, py2 = int(w * 0.05), int(h * 0.20), int(w * 0.40), int(h * 0.75)
        portrait_crop = image_rgb[py1:py2, px1:px2]

        if portrait_crop.size > 0:
            out_path = os.path.join(settings.OUTPUT_DIR, f"{doc_id}_portrait.jpg")
            save_image_rgb(portrait_crop, out_path)
            bbox = BoundingBox(x=px1, y=py1, width=px2 - px1, height=py2 - py1)
            return out_path, bbox, True

        return None, None, False
