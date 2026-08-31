import numpy as np
from typing import Dict, Any, Tuple
from pydantic import BaseModel, Field

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from app.schemas.document import QualityResult
from app.core.logging import get_logger

logger = get_logger("quality_analyzer")

class ExtendedQualityMetrics(BaseModel):
    width: int
    height: int
    aspect_ratio: float
    blur_score: float
    is_blurred: bool
    brightness_score: float  # Mean intensity [0..255]
    contrast_score: float    # Standard deviation of intensity
    glare_score: float       # Overexposure pixel ratio [0..1]
    has_glare: bool
    estimated_dpi: int
    completeness_score: float  # Margin / boundary score [0..1]
    orientation_angle: float   # Estimated rotation angle in degrees
    is_skewed: bool
    overall_quality_score: float = Field(..., ge=0.0, le=1.0)
    is_acceptable: bool

class QualityAnalyzer:
    """OpenCV-based document image quality analyzer."""

    def __init__(self,
                 blur_threshold: float = 100.0,
                 glare_threshold: float = 0.08,
                 min_acceptable_score: float = 0.60):
        self.blur_threshold = blur_threshold
        self.glare_threshold = glare_threshold
        self.min_acceptable_score = min_acceptable_score

    def analyze(self, image_rgb: np.ndarray, processed_path: str = "") -> QualityResult:
        """Analyze RGB numpy image quality and return normalized QualityResult."""
        metrics = self.compute_metrics(image_rgb)
        
        return QualityResult(
            quality_score=round(metrics.overall_quality_score, 2),
            blur_score=round(metrics.blur_score, 2),
            is_blurred=metrics.is_blurred,
            glare_score=round(metrics.glare_score, 3),
            has_glare=metrics.has_glare,
            resolution_dpi=metrics.estimated_dpi,
            is_skewed=metrics.is_skewed,
            deskew_angle=round(metrics.orientation_angle, 2),
            completeness_score=round(metrics.completeness_score, 2),
            processed_image_path=processed_path,
            is_acceptable=metrics.is_acceptable
        )

    def compute_metrics(self, image_rgb: np.ndarray) -> ExtendedQualityMetrics:
        """Calculate detailed quality metrics for the input image."""
        if image_rgb is None or image_rgb.size == 0:
            return ExtendedQualityMetrics(
                width=0, height=0, aspect_ratio=0.0,
                blur_score=0.0, is_blurred=True,
                brightness_score=0.0, contrast_score=0.0,
                glare_score=1.0, has_glare=True,
                estimated_dpi=72, completeness_score=0.0,
                orientation_angle=0.0, is_skewed=False,
                overall_quality_score=0.0, is_acceptable=False
            )

        h, w = image_rgb.shape[:2]
        aspect_ratio = float(w / h) if h > 0 else 0.0

        # Grayscale conversion
        if HAS_CV2:
            gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        else:
            gray = np.mean(image_rgb, axis=2).astype(np.uint8)

        # 1. Blur Detection (Laplacian variance)
        if HAS_CV2:
            blur_val = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        else:
            blur_val = float(np.var(gray))

        is_blurred = blur_val < self.blur_threshold

        # 2. Brightness & Contrast
        brightness_val = float(np.mean(gray))
        contrast_val = float(np.std(gray))

        # 3. Glare / Overexposure Ratio
        glare_pixels = np.sum(gray >= 245)
        glare_val = float(glare_pixels / gray.size) if gray.size > 0 else 0.0
        has_glare = glare_val > self.glare_threshold

        # 4. Estimated DPI / Resolution adequacy
        # Standard ID cards are roughly 3.375 x 2.125 inches (85.6mm x 54mm)
        # 300 DPI ID card image is ~ 1012 x 638 pixels
        min_dim = min(w, h)
        if min_dim >= 1000:
            estimated_dpi = 300
        elif min_dim >= 600:
            estimated_dpi = 200
        elif min_dim >= 400:
            estimated_dpi = 150
        else:
            estimated_dpi = 72

        # 5. Completeness Check (Border Margin & Pixel Variance at edges)
        completeness_score = self._check_completeness(gray)

        # 6. Orientation / Skew Estimation
        skew_angle, is_skewed = self._estimate_skew(gray)

        # 7. Composite Normalized Quality Score [0.0 - 1.0]
        # Start at 1.0 and deduct based on defects
        score = 1.0

        # Blur penalty
        if blur_val < 30.0:
            score -= 0.40
        elif blur_val < self.blur_threshold:
            score -= 0.20

        # Glare penalty
        if glare_val > 0.15:
            score -= 0.30
        elif glare_val > self.glare_threshold:
            score -= 0.15

        # Brightness penalty (extreme dark < 50 or extreme light > 220)
        if brightness_val < 40 or brightness_val > 230:
            score -= 0.25
        elif brightness_val < 70 or brightness_val > 200:
            score -= 0.10

        # Low contrast penalty
        if contrast_val < 25.0:
            score -= 0.20

        # Resolution penalty
        if min_dim < 300:
            score -= 0.30
        elif min_dim < 600:
            score -= 0.10

        # Completeness penalty
        if completeness_score < 0.5:
            score -= 0.20

        normalized_score = float(max(0.0, min(1.0, score)))
        is_acceptable = normalized_score >= self.min_acceptable_score

        return ExtendedQualityMetrics(
            width=w,
            height=h,
            aspect_ratio=round(aspect_ratio, 3),
            blur_score=blur_val,
            is_blurred=is_blurred,
            brightness_score=round(brightness_val, 2),
            contrast_score=round(contrast_val, 2),
            glare_score=glare_val,
            has_glare=has_glare,
            estimated_dpi=estimated_dpi,
            completeness_score=completeness_score,
            orientation_angle=skew_angle,
            is_skewed=is_skewed,
            overall_quality_score=normalized_score,
            is_acceptable=is_acceptable
        )

    def _check_completeness(self, gray: np.ndarray) -> float:
        """Basic check to determine if the document borders are fully within the image frame."""
        h, w = gray.shape
        if h < 10 or w < 10:
            return 0.0

        # Sample top, bottom, left, right 3-pixel borders
        top_border = gray[:3, :]
        bottom_border = gray[-3:, :]
        left_border = gray[:, :3]
        right_border = gray[:, -3:]

        # If borders have high variance, document edges might be cropped off
        border_stds = [np.std(top_border), np.std(bottom_border), np.std(left_border), np.std(right_border)]
        avg_border_std = float(np.mean(border_stds))

        # Standard score: 1.0 if clean uniform background, lower if cluttered or truncated
        if avg_border_std < 40.0:
            return 1.0
        elif avg_border_std < 60.0:
            return 0.8
        else:
            return 0.6

    def _estimate_skew(self, gray: np.ndarray) -> Tuple[float, bool]:
        """Estimate image skew angle using edge detection and Hough lines if available."""
        if not HAS_CV2:
            return 0.0, False

        try:
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
            if lines is None or len(lines) == 0:
                return 0.0, False

            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                if x2 - x1 == 0:
                    continue
                angle = np.arctan2(y2 - y1, x2 - x1) * 180.0 / np.pi
                if -45.0 <= angle <= 45.0:
                    angles.append(angle)

            if len(angles) > 0:
                median_angle = float(np.median(angles))
                is_skewed = abs(median_angle) > 2.0
                return median_angle, is_skewed
        except Exception:
            pass

        return 0.0, False
