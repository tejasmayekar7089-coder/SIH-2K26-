import os
import numpy as np
from app.schemas.document import ValidatedInputDocument, QualityResult
from app.modules.acquisition.loader import DocumentLoader, DocumentLoadingError
from app.modules.acquisition.quality import QualityAnalyzer
from app.modules.acquisition.preprocessor import ImagePreprocessor
from app.utils.image_utils import save_image_rgb
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("acquisition")

class AcquisitionService:
    """Module 2: Acquisition, Document Loading, OpenCV Quality Analysis & Preprocessing."""

    def __init__(self,
                 quality_analyzer: QualityAnalyzer = None,
                 preprocessor: ImagePreprocessor = None):
        self.quality_analyzer = quality_analyzer or QualityAnalyzer(
            blur_threshold=100.0,
            glare_threshold=0.08,
            min_acceptable_score=settings.QUALITY_MIN_SCORE
        )
        self.preprocessor = preprocessor or ImagePreprocessor(max_dimension=2000)

    def evaluate_and_preprocess(self, doc: ValidatedInputDocument) -> QualityResult:
        """Loads document/image safely, performs OpenCV quality evaluation and outputs preprocessed image."""
        logger.info(f"Processing acquisition & quality for doc: {doc.document_id} ({doc.storage_path})")

        # 1. Safe Document Loading
        try:
            pages = DocumentLoader.load_pages_rgb(doc.storage_path)
            primary_image_rgb = pages[0]
        except DocumentLoadingError as e:
            logger.error(f"Document loading failed for {doc.document_id}: {e}")
            return QualityResult(
                quality_score=0.0,
                blur_score=0.0,
                is_blurred=True,
                glare_score=1.0,
                has_glare=True,
                processed_image_path=doc.storage_path,
                is_acceptable=False
            )
        except Exception as e:
            logger.error(f"Unexpected error loading document {doc.document_id}: {e}")
            return QualityResult(
                quality_score=0.0,
                blur_score=0.0,
                is_blurred=True,
                glare_score=1.0,
                has_glare=True,
                processed_image_path=doc.storage_path,
                is_acceptable=False
            )

        # 2. Quality Analysis
        quality_metrics = self.quality_analyzer.compute_metrics(primary_image_rgb)

        # 3. Preprocessing (non-destructive; original is preserved on disk)
        processed_rgb = self.preprocessor.preprocess(
            image_rgb=primary_image_rgb,
            deskew_angle=quality_metrics.orientation_angle,
            enhance_contrast=True,
            denoise=True
        )

        # 4. Save preprocessed image separately
        out_path = os.path.join(settings.OUTPUT_DIR, f"{doc.document_id}_processed.jpg")
        save_image_rgb(processed_rgb, out_path)

        # 5. Return normalized QualityResult
        return self.quality_analyzer.analyze(primary_image_rgb, processed_path=out_path)
