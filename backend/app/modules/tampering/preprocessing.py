import os
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("tampering_preprocessing")

class TamperingPreprocessor:
    """Computes signal-level Error Level Analysis (ELA) and Spatial Rich Model (SRM) noise maps."""

    @staticmethod
    def compute_ela_diff(image_rgb: np.ndarray, quality: int = None) -> np.ndarray:
        """
        Computes JPEG Error Level Analysis (ELA) pixel residual map.
        Re-compresses image at specified quality and computes absolute pixel difference.
        """
        q = quality or settings.TAMPER_ELA_QUALITY
        if image_rgb is None or image_rgb.size == 0:
            return np.zeros((100, 100), dtype=np.uint8)

        try:
            pil_orig = Image.fromarray(image_rgb)
            tmp_path = os.path.join(settings.OUTPUT_DIR, f"temp_ela_{os.getpid()}.jpg")
            pil_orig.save(tmp_path, 'JPEG', quality=q)
            pil_recomp = Image.open(tmp_path)

            diff = ImageChops.difference(pil_orig, pil_recomp)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

            extrema = diff.getextrema()
            max_diff = max([ex[1] for ex in extrema]) if extrema else 1
            scale = 255.0 / max_diff if max_diff != 0 else 1.0
            enhanced = ImageEnhance.Brightness(diff).enhance(scale)
            
            ela_cv = cv2.cvtColor(np.array(enhanced), cv2.COLOR_RGB2GRAY)
            return ela_cv
        except Exception as e:
            logger.warning(f"ELA calculation exception: {e}")
            h, w = image_rgb.shape[:2]
            return np.zeros((h, w), dtype=np.uint8)

    @staticmethod
    def compute_srm_noise_map(image_rgb: np.ndarray) -> np.ndarray:
        """
        Computes High-Pass Spatial Rich Model (SRM) noise variance residual map.
        Highlights high-frequency noise discontinuities across spatial image regions.
        """
        if image_rgb is None or image_rgb.size == 0:
            return np.zeros((100, 100), dtype=np.uint8)

        try:
            gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY) if len(image_rgb.shape) == 3 else image_rgb
            
            # SRM 5x5 High-Pass Kernel
            srm_kernel = np.array([
                [0,  0,  0,  0,  0],
                [0, -1,  2, -1,  0],
                [0,  2, -4,  2,  0],
                [0, -1,  2, -1,  0],
                [0,  0,  0,  0,  0]
            ], dtype=np.float32) / 4.0

            filtered = cv2.filter2D(gray.astype(np.float32), -1, srm_kernel)
            noise_var = np.abs(filtered)
            noise_norm = cv2.normalize(noise_var, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
            return noise_norm
        except Exception as e:
            logger.warning(f"SRM noise map exception: {e}")
            h, w = image_rgb.shape[:2]
            return np.zeros((h, w), dtype=np.uint8)

    @classmethod
    def fuse_anomaly_maps(cls, ela_map: np.ndarray, noise_map: np.ndarray, srm_weight: float = None) -> np.ndarray:
        """Fuses ELA residual intensity with SRM noise variance into a single 2D anomaly map."""
        w_srm = srm_weight if srm_weight is not None else settings.TAMPER_SRM_WEIGHT
        w_ela = 1.0 - w_srm

        if ela_map.shape != noise_map.shape:
            noise_map = cv2.resize(noise_map, (ela_map.shape[1], ela_map.shape[0]))

        fused = cv2.addWeighted(ela_map, w_ela, noise_map, w_srm, 0)
        return fused
