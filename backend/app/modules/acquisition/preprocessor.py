import numpy as np
from typing import Tuple, Optional
from PIL import Image, ImageOps

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from app.core.logging import get_logger

logger = get_logger("image_preprocessor")

class ImagePreprocessor:
    """Non-destructive image preprocessor to improve quality for downstream OCR."""

    def __init__(self, max_dimension: int = 2000):
        self.max_dimension = max_dimension

    def preprocess(self,
                   image_rgb: np.ndarray,
                   deskew_angle: float = 0.0,
                   enhance_contrast: bool = True,
                   denoise: bool = True) -> np.ndarray:
        """
        Safely preprocess image without aggressively altering original features.
        - Correct orientation/rotation if angle provided
        - Resize preserving aspect ratio
        - Contrast enhancement via CLAHE
        - Subtle denoising
        """
        if image_rgb is None or image_rgb.size == 0:
            return image_rgb

        img = image_rgb.copy()

        # 1. Orientation Correction / Rotate if skew angle detected
        if abs(deskew_angle) > 1.0 and abs(deskew_angle) < 45.0:
            img = self.rotate_image(img, -deskew_angle)

        # 2. Resize preserving aspect ratio if larger than max_dimension
        img = self.resize_max_dimension(img, self.max_dimension)

        # 3. Contrast enhancement using CLAHE (on LAB color space)
        if enhance_contrast and HAS_CV2:
            img = self.apply_clahe_rgb(img)

        # 4. Light Denoising preserving text edges
        if denoise and HAS_CV2:
            img = cv2.fastNlMeansDenoisingColored(img, None, 3, 3, 7, 21)

        return img

    @staticmethod
    def rotate_image(image_rgb: np.ndarray, angle_degrees: float) -> np.ndarray:
        """Rotate RGB numpy image by specified angle in degrees."""
        if abs(angle_degrees) < 0.1:
            return image_rgb

        if HAS_CV2:
            h, w = image_rgb.shape[:2]
            center = (w // 2, h // 2)
            matrix = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
            return cv2.warpAffine(image_rgb, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        else:
            pil_img = Image.fromarray(image_rgb)
            rotated_pil = pil_img.rotate(angle_degrees, expand=False, resample=Image.Resampling.BICUBIC)
            return np.array(rotated_pil)

    @staticmethod
    def resize_max_dimension(image_rgb: np.ndarray, max_dim: int = 2000) -> np.ndarray:
        """Resize image to fit within max_dim while strictly preserving aspect ratio."""
        h, w = image_rgb.shape[:2]
        if max(h, w) <= max_dim:
            return image_rgb

        scale = max_dim / float(max(h, w))
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))

        if HAS_CV2:
            return cv2.resize(image_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        else:
            pil_img = Image.fromarray(image_rgb)
            resized_pil = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            return np.array(resized_pil)

    @staticmethod
    def to_grayscale(image_rgb: np.ndarray) -> np.ndarray:
        """Convert RGB image to 8-bit single channel grayscale."""
        if HAS_CV2:
            return cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        else:
            pil_img = Image.fromarray(image_rgb).convert("L")
            return np.array(pil_img)

    @staticmethod
    def apply_clahe_rgb(image_rgb: np.ndarray) -> np.ndarray:
        """Apply Contrast Limited Adaptive Histogram Equalization to L-channel in LAB color space."""
        if not HAS_CV2:
            return image_rgb

        try:
            lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
            l_channel, a_channel, b_channel = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l_channel)
            limg = cv2.merge((cl, a_channel, b_channel))
            return cv2.cvtColor(limg, cv2.COLOR_LAB2RGB)
        except Exception:
            return image_rgb
