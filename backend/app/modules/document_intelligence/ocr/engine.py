from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np

from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.core.logging import get_logger

logger = get_logger("ocr_engine")

try:
    from rapidocr_onnxruntime import RapidOCR
    HAS_RAPID_OCR = True
except ImportError:
    HAS_RAPID_OCR = False

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
    """PaddleOCR / RapidOCR primary engine implementation."""

    def __init__(self, lang: str = "en", use_angle_cls: bool = True, use_gpu: bool = False):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._rapid_ocr = None
        self._paddle_ocr = None
        self._initialized = False

    def _initialize_engine(self):
        """Lazy initialization of OCR instance."""
        if self._initialized:
            return

        if HAS_RAPID_OCR:
            try:
                logger.info("Initializing RapidOCR (ONNX runtime backend)...")
                self._rapid_ocr = RapidOCR()
                self._initialized = True
                logger.info("RapidOCR initialized successfully.")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize RapidOCR: {e}")

        if HAS_PADDLE_OCR:
            try:
                logger.info("Initializing PaddleOCR engine...")
                try:
                    self._paddle_ocr = PaddleOCR(lang=self.lang)
                except Exception:
                    self._paddle_ocr = PaddleOCR()
                self._initialized = True
                logger.info("PaddleOCR engine initialized successfully.")
                return
            except Exception as e:
                logger.warning(f"Failed to initialize PaddleOCR engine: {e}")

        logger.warning("No accelerated OCR backend available. Operating in fallback mode.")
        self._initialized = False

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Run OCR on image and convert results to normalized OCRResult structure."""
        self._initialize_engine()

        if not self._initialized:
            fallback = FallbackOCREngine()
            return fallback.process_image(image_rgb, page_index=page_index)

        try:
            import cv2
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)

            items: List[OCRItem] = []

            # 1. RapidOCR execution path
            if self._rapid_ocr is not None:
                raw_results, _ = self._rapid_ocr(image_bgr)
                if raw_results:
                    for line in raw_results:
                        box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                        text = str(line[1]).strip()
                        confidence = float(line[2])

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

                    result = OCRResult(items=items, engine_name="PaddleOCR-ONNX")
                    result.rebuild_full_text()
                    return result

            # 2. PaddleOCR execution path
            if self._paddle_ocr is not None:
                raw_results = self._paddle_ocr.ocr(image_bgr)
                if raw_results and len(raw_results) > 0 and raw_results[0] is not None:
                    for line in raw_results[0]:
                        box = line[0]
                        text_info = line[1]
                        text = text_info[0]
                        confidence = float(text_info[1])

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

            fallback = FallbackOCREngine()
            return fallback.process_image(image_rgb, page_index=page_index)

        except Exception as e:
            logger.error(f"Error executing OCR engine: {e}")
            fallback = FallbackOCREngine()
            return fallback.process_image(image_rgb, page_index=page_index)

class FallbackOCREngine(BaseOCREngine):
    """Fallback OCR engine when OCR dependencies or weights are not loaded."""

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Returns normalized empty or basic structure."""
        return OCRResult(
            items=[],
            full_text="",
            mean_confidence=0.0,
            engine_name="FallbackOCREngine"
        )
