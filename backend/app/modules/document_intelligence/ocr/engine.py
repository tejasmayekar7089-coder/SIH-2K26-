from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import numpy as np

from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.acquisition.preprocessor import ImagePreprocessor
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
    """PaddleOCR / RapidOCR primary engine implementation with multi-pass preprocessing retries."""

    def __init__(self, lang: str = "en", use_angle_cls: bool = True, use_gpu: bool = False):
        self.lang = lang
        self.use_angle_cls = use_angle_cls
        self.use_gpu = use_gpu
        self._rapid_ocr = None
        self._paddle_ocr = None
        self._initialized = False

    def _initialize_engine(self):
        """Lazy initialization of available OCR backends."""
        if self._initialized:
            return

        if HAS_RAPID_OCR:
            try:
                logger.info("[OCR] Initializing RapidOCR (ONNX runtime engine)...")
                self._rapid_ocr = RapidOCR()
                logger.info("[OCR] RapidOCR engine initialized successfully.")
            except Exception as e:
                logger.warning(f"[OCR] Failed to initialize RapidOCR: {e}")

        if HAS_PADDLE_OCR and self._paddle_ocr is None:
            try:
                logger.info("[OCR] Initializing PaddleOCR engine...")
                try:
                    self._paddle_ocr = PaddleOCR(lang=self.lang, use_angle_cls=False)
                except Exception:
                    self._paddle_ocr = PaddleOCR()
                logger.info("[OCR] PaddleOCR engine initialized successfully.")
            except Exception as e:
                logger.warning(f"[OCR] Failed to initialize PaddleOCR engine: {e}")

        if self._rapid_ocr is not None or self._paddle_ocr is not None:
            self._initialized = True
        else:
            logger.warning("[OCR] No accelerated OCR backend available. Operating in fallback mode.")
            self._initialized = False

    def _run_single_ocr_pass(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Runs single pass OCR on a specific image variant."""
        items: List[OCRItem] = []
        engine_name = "FallbackOCREngine"

        if image_rgb is None or image_rgb.size == 0:
            return OCRResult(items=[], full_text="", mean_confidence=0.0, engine_name=engine_name)

        try:
            import cv2
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR) if len(image_rgb.shape) == 3 else image_rgb

            # 1. Primary RapidOCR path
            if self._rapid_ocr is not None:
                try:
                    raw_results, _ = self._rapid_ocr(image_bgr)
                    if raw_results:
                        for line in raw_results:
                            box = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                            text = str(line[1]).strip()
                            confidence = float(line[2])

                            if not text:
                                continue

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
                except Exception as e:
                    logger.warning(f"[OCR] RapidOCR pass exception: {e}")

            # 2. Fallback PaddleOCR path
            if self._paddle_ocr is not None:
                try:
                    raw_results = self._paddle_ocr.ocr(image_bgr)
                    if raw_results and len(raw_results) > 0 and raw_results[0] is not None:
                        for line in raw_results[0]:
                            box = line[0]
                            text_info = line[1]
                            text = str(text_info[0]).strip()
                            confidence = float(text_info[1])

                            if not text:
                                continue

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
                    logger.warning(f"[OCR] PaddleOCR pass exception: {e}")

        except Exception as e:
            logger.error(f"[OCR] Execution error: {e}")

        return OCRResult(items=[], full_text="", mean_confidence=0.0, engine_name=engine_name)

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """
        Run robust multi-pass OCR on image.
        Evaluates preprocessing variants and rotational retries to guarantee best extraction.
        """
        self._initialize_engine()

        if not self._initialized:
            return FallbackOCREngine().process_image(image_rgb, page_index=page_index)

        # 1. First pass on primary preprocessed image
        best_result = self._run_single_ocr_pass(image_rgb, page_index=page_index)
        logger.info(f"[OCR] Primary pass: found {len(best_result.items)} detections (mean conf: {best_result.mean_confidence:.2f})")

        # If primary pass yields good results (>= 5 items and mean confidence >= 0.50), return directly
        if len(best_result.items) >= 5 and best_result.mean_confidence >= 0.50:
            return best_result

        # 2. Multi-pass retry strategy with preprocessing variants
        preprocessor = ImagePreprocessor()
        variants = preprocessor.get_preprocessing_variants(image_rgb)

        for name, variant_img in variants:
            if name == "original":
                continue
            res = self._run_single_ocr_pass(variant_img, page_index=page_index)
            logger.info(f"[OCR] Variant pass [{name}]: found {len(res.items)} detections (mean conf: {res.mean_confidence:.2f})")
            if len(res.items) > len(best_result.items) or (len(res.items) == len(best_result.items) and res.mean_confidence > best_result.mean_confidence):
                best_result = res

        # 3. Rotational retries (90, 180, 270 degrees) if text is still poor (< 3 items)
        if len(best_result.items) < 3:
            for angle in [90, 180, 270]:
                rot_img = preprocessor.rotate_image(image_rgb, angle)
                res = self._run_single_ocr_pass(rot_img, page_index=page_index)
                logger.info(f"[OCR] Rotation pass [{angle}°]: found {len(res.items)} detections (mean conf: {res.mean_confidence:.2f})")
                if len(res.items) > len(best_result.items):
                    best_result = res
                    break

        return best_result

class FallbackOCREngine(BaseOCREngine):
    """Fallback OCR engine when OCR dependencies or weights are not loaded."""

    def process_image(self, image_rgb: np.ndarray, page_index: int = 0) -> OCRResult:
        """Returns normalized empty structure."""
        return OCRResult(
            items=[],
            full_text="",
            mean_confidence=0.0,
            engine_name="FallbackOCREngine"
        )

