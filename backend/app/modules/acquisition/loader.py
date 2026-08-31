import os
import io
from typing import List, Tuple, Optional
import numpy as np
from PIL import Image

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

from app.core.logging import get_logger

logger = get_logger("document_loader")

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
SUPPORTED_DOCUMENT_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS.union({".pdf"})

class DocumentLoadingError(Exception):
    """Custom exception raised when document/image loading fails."""
    pass

class DocumentLoader:
    """Reusable loader for multi-format documents and images."""

    @staticmethod
    def is_supported(file_path_or_name: str) -> bool:
        """Check if file format extension is supported."""
        ext = os.path.splitext(file_path_or_name)[1].lower()
        return ext in SUPPORTED_DOCUMENT_EXTENSIONS

    @classmethod
    def load_pages_rgb(cls, file_path: str, dpi: int = 300) -> List[np.ndarray]:
        """
        Safely load document or image into a list of RGB numpy arrays (one array per page).
        Supports: JPG, JPEG, PNG, WEBP, TIFF, and PDF.
        """
        if not os.path.exists(file_path):
            raise DocumentLoadingError(f"File does not exist: {file_path}")

        if os.path.getsize(file_path) == 0:
            raise DocumentLoadingError(f"File is empty (0 bytes): {file_path}")

        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return cls._load_pdf_pages(file_path, dpi=dpi)
        elif ext in SUPPORTED_IMAGE_EXTENSIONS:
            img = cls._load_single_image(file_path)
            return [img]
        else:
            raise DocumentLoadingError(f"Unsupported file format extension: {ext}")

    @classmethod
    def load_single_page_rgb(cls, file_path: str, page_index: int = 0, dpi: int = 300) -> np.ndarray:
        """Load a specific page as an RGB numpy array."""
        pages = cls.load_pages_rgb(file_path, dpi=dpi)
        if page_index < 0 or page_index >= len(pages):
            raise DocumentLoadingError(f"Page index {page_index} out of range (total pages: {len(pages)})")
        return pages[page_index]

    @staticmethod
    def _load_single_image(file_path: str) -> np.ndarray:
        """Safely load an image file to RGB numpy array."""
        try:
            if HAS_CV2:
                bgr = cv2.imread(file_path, cv2.IMREAD_COLOR)
                if bgr is not None and bgr.size > 0:
                    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
            
            # Fallback to PIL
            with Image.open(file_path) as pil_img:
                pil_img = pil_img.convert("RGB")
                img_array = np.array(pil_img)
                if img_array.size == 0:
                    raise DocumentLoadingError(f"Loaded image has 0 pixels: {file_path}")
                return img_array
        except Exception as e:
            if isinstance(e, DocumentLoadingError):
                raise
            raise DocumentLoadingError(f"Failed to load image '{file_path}': {str(e)}") from e

    @staticmethod
    def _load_pdf_pages(pdf_path: str, dpi: int = 300) -> List[np.ndarray]:
        """Render PDF pages to RGB numpy arrays using PyMuPDF."""
        if not HAS_PYMUPDF:
            raise DocumentLoadingError("PyMuPDF (fitz) is not installed. Unable to render PDF files.")

        try:
            doc = fitz.open(pdf_path)
            if doc.is_encrypted:
                raise DocumentLoadingError(f"PDF is encrypted/password protected: {pdf_path}")

            if len(doc) == 0:
                raise DocumentLoadingError(f"PDF document contains 0 pages: {pdf_path}")

            zoom = dpi / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pages = []

            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap(matrix=mat, alpha=False)
                img_data = pix.samples
                img_array = np.frombuffer(img_data, dtype=np.uint8).reshape((pix.height, pix.width, 3))
                pages.append(img_array)

            doc.close()
            return pages
        except Exception as e:
            if isinstance(e, DocumentLoadingError):
                raise
            raise DocumentLoadingError(f"Failed to render PDF document '{pdf_path}': {str(e)}") from e
