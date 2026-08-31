import pytest
import numpy as np
from app.modules.acquisition.quality import QualityAnalyzer, ExtendedQualityMetrics

def test_quality_analysis_clear_image():
    # Sharp gradient image
    img = np.zeros((600, 800, 3), dtype=np.uint8)
    img[::10, :, :] = 255  # grid pattern for high variance
    img[:, ::10, :] = 255

    analyzer = QualityAnalyzer()
    metrics = analyzer.compute_metrics(img)

    assert metrics.width == 800
    assert metrics.height == 600
    assert metrics.aspect_ratio == 1.333
    assert metrics.blur_score > 100.0
    assert metrics.is_blurred is False
    assert 0.0 <= metrics.overall_quality_score <= 1.0

def test_quality_analysis_blurred_image():
    # Constant smooth image with near zero variance
    img = np.full((500, 500, 3), fill_value=128, dtype=np.uint8)

    analyzer = QualityAnalyzer()
    metrics = analyzer.compute_metrics(img)

    assert metrics.blur_score < 10.0
    assert metrics.is_blurred is True
    assert metrics.overall_quality_score < 0.8

def test_quality_analysis_glare_image():
    # Image with saturated white glare block (> 245)
    img = np.zeros((400, 400, 3), dtype=np.uint8)
    img[:200, :200, :] = 255  # 25% glare coverage

    analyzer = QualityAnalyzer()
    metrics = analyzer.compute_metrics(img)

    assert metrics.glare_score == pytest.approx(0.25, abs=0.01)
    assert metrics.has_glare is True

def test_quality_analysis_empty_array():
    img = np.array([], dtype=np.uint8)

    analyzer = QualityAnalyzer()
    result = analyzer.analyze(img)

    assert result.quality_score == 0.0
    assert result.is_acceptable is False
