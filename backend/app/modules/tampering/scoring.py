import numpy as np
from typing import List, Dict, Tuple, Any
from app.schemas.tampering import SuspiciousRegion
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("tampering_scoring")

class TamperingScorer:
    """Computes dynamic confidence scores, risk levels, and anomaly types without hardcoded fake values."""

    @classmethod
    def evaluate(
        cls,
        fused_map: np.ndarray,
        suspicious_regions: List[SuspiciousRegion],
        correlations: List[Dict[str, Any]]
    ) -> Tuple[float, bool, str, List[str]]:
        """
        Derives confidence score (0.0 - 1.0), tampering_detected (bool), risk_level (LOW, MEDIUM, HIGH),
        and list of unique tampering_types based on empirical image anomaly density and field correlation.
        """
        if fused_map is None or fused_map.size == 0:
            return 0.0, False, "LOW", []

        # 1. Pixel Anomaly Proportion Score
        mean_val, std_val = cv2_mean_std(fused_map)
        threshold_cutoff = mean_val + (2.0 * std_val)
        elevated_pixels = np.sum(fused_map > threshold_cutoff)
        pixel_anomaly_ratio = float(elevated_pixels) / float(fused_map.size)
        
        base_score = min(0.60, pixel_anomaly_ratio * 12.0)

        # 2. Suspicious Region Contribution Score
        region_score = 0.0
        if suspicious_regions:
            avg_region_anomaly = sum(r.anomaly_score for r in suspicious_regions) / float(len(suspicious_regions))
            region_score = min(0.40, len(suspicious_regions) * 0.08 + avg_region_anomaly * 0.20)

        # 3. Field Correlation Overlap Multiplier
        field_bonus = 0.0
        if correlations:
            field_bonus = min(0.25, len(correlations) * 0.08)

        # 4. Final Aggregated Confidence Score
        confidence = min(1.0, round(float(base_score + region_score + field_bonus), 2))

        # 5. Threshold & Risk Level Determination
        alert_thresh = getattr(settings, "TAMPER_ALERT_THRESHOLD", 0.35)
        high_risk_thresh = getattr(settings, "TAMPER_HIGH_RISK_THRESHOLD", 0.70)

        tampering_detected = confidence >= alert_thresh

        if confidence >= high_risk_thresh:
            risk_level = "HIGH"
        elif confidence >= alert_thresh:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # 6. Extract Unique Tampering Types
        tampering_types_set = set()
        for r in suspicious_regions:
            if r.anomaly_type:
                tampering_types_set.add(r.anomaly_type)
        for c in correlations:
            if c.get("anomaly_type"):
                tampering_types_set.add(c["anomaly_type"])

        tampering_types = sorted(list(tampering_types_set))
        if tampering_detected and not tampering_types:
            tampering_types = ["IMAGE_INCONSISTENCY"]

        return confidence, tampering_detected, risk_level, tampering_types

def cv2_mean_std(img: np.ndarray) -> Tuple[float, float]:
    """Helper to compute mean and std dev of numpy array."""
    mean_val = float(np.mean(img))
    std_val = float(np.std(img))
    return mean_val, std_val
