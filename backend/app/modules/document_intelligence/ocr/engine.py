from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.core.logging import get_logger

logger = get_logger("ocr_engine")

try:
    from paddleocr import PaddleOCR
    HAS_PADDLE_OCR = True
except ImportError:
    HAS_PADDLE_OCR = False

class BaseOCREngine(ABC):
    """Abstract base class for independent OCR engines."""

    @abstractmethod
    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Process RGB numpy image and return normalized OCRResult."""
        pass

class PaddleOCREngine(BaseOCREngine):
    """PaddleOCR primary engine implementation."""

    def __init__(self, lang: str = "en", use_angle_cls: bool = True, use_gpu: bool = False):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._ocr = None
        self._initialized = False

    def _initialize_engine(self):
        """Lazy initialization of PaddleOCR instance."""
        if self._initialized:
            return
        if not HAS_PADDLE_OCR:
            logger.warning("PaddleOCR package is not installed. PaddleOCREngine will operate in fallback mode.")
            self._initialized = False
            return
        try:
            logger.info("Initializing PaddleOCR engine...")
            # PaddleOCR initialization signature
            self._ocr = PaddleOCR(use_angle_cls=self.use_angle_cls, lang=self.lang, use_gpu=self.use_gpu, show_log=False)
            self._initialized = True
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PaddleOCR engine: {e}")
            self._ocr = None
            self._initialized = False

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Run PaddleOCR on image and convert results to normalized OCRResult structure."""
        self._initialize_engine()

        if not self._initialized or self._ocr is None:
            # Fallback to secondary OCR / empty handler
            fallback = FallbackOCREngine()
            return fallback.process_image(image_rgb, page_index=page_index)

        try:
            # Convert RGB to BGR for OpenCV/PaddleOCR standard input if needed
            import cv2
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            raw_results = self._ocr.ocr(image_bgr, cls=self.use_angle_cls)

            items: List[OCRItem] = []
            if raw_results and len(raw_results) > 0 and raw_results[0] is not None:
                for line in raw_results[0]:
                    box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    text_info = line[1]  # (text, confidence)
                    text = text_info[0]
                    confidence = float(text_info[1])

                    # Calculate axis-aligned bounding box (x, y, width, height)
                    xs = [pt[0] for pt in box]
                    ys = [pt[1] for pt in box]
                    min_x, max_x = int(min(xs)), int(max(xs))
                    min_y, max_y = int(min(ys)), int(max(ys))
                    bbox = BoundingBox(
                        x=max(0, min_x),
                        y=max(0, min_y),
                        width=max(1, max_x - min_x),
                        height=max(1, max_y - min_y)
                    )

                    items.append(OCRItem(
                        text=text,
                        confidence=round(confidence, 4),
                        bounding_box=bbox,
                        page_index=page_index
                    ))

            result = OCRResult(items=items, engine_name="PaddleOCR")
            result.rebuild_full_text()
            return result

        except Exception as e:
            logger.error(f"Error executing PaddleOCR: {e}")
            fallback = FallbackOCREngine()
            return fallback.process_image(image_rgb, page_index=page_index)

class FallbackOCREngine(BaseOCREngine):
    """Fallback OCR engine when PaddleOCR dependencies or weights are not loaded."""

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Returns normalized empty or basic structure."""
        return OCRResult(
            items=[],
            full_text="",
            mean_confidence=0.0,
            engine_name="FallbackOCREngine"
        )
