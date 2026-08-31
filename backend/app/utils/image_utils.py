try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

import numpy as np
import base64
import os
from PIL import Image

def load_image_rgb(image_path: str) -> np.ndarray:
    """Load image safely from disk in RGB format."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")
    if HAS_CV2:
        bgr = cv2.imread(image_path)
        if bgr is not None:
            return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    # Pillow fallback
    with Image.open(image_path) as img:
        return np.array(img.convert('RGB'))

def save_image_rgb(image_rgb: np.ndarray, output_path: str) -> str:
    """Save RGB numpy image to disk."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if HAS_CV2:
        bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, bgr)
    else:
        img = Image.fromarray(image_rgb)
        img.save(output_path)
    return output_path

def compute_laplacian_variance(image_rgb: np.ndarray) -> float:
    """Compute focus/blur metric using Laplacian variance."""
    if HAS_CV2:
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())
    # Variance fallback
    gray = np.mean(image_rgb, axis=2)
    return float(np.var(gray))

def compute_glare_ratio(image_rgb: np.ndarray, threshold: int = 245) -> float:
    """Calculate ratio of saturated specular reflection pixels."""
    if HAS_CV2:
        gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    else:
        gray = np.mean(image_rgb, axis=2)
    glare_pixels = np.sum(gray >= threshold)
    total_pixels = gray.size
    return float(glare_pixels / total_pixels) if total_pixels > 0 else 0.0

def generate_heatmap_overlay(image_rgb: np.ndarray, mask: np.ndarray, alpha: float = 0.5) -> np.ndarray:
    """Generate color jet heatmap overlaid on original RGB image."""
    mask_normalized = np.uint8(np.clip(mask, 0.0, 1.0) * 255)
    if HAS_CV2:
        heatmap_bgr = cv2.applyColorMap(mask_normalized, cv2.COLORMAP_JET)
        heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)
        overlay = cv2.addWeighted(image_rgb, 1 - alpha, heatmap_rgb, alpha, 0)
        return overlay
    # Fallback pseudo-color overlay using numpy
    overlay = image_rgb.copy()
    overlay[..., 0] = np.uint8(np.clip(overlay[..., 0] * (1 - alpha) + mask_normalized * alpha, 0, 255))
    return overlay

def encode_image_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')
