from typing import List, Dict, Any, Tuple, Optional
from app.schemas.common import EvidenceItem, SeverityLevel
from app.schemas.tampering import SuspiciousRegion
from app.core.logging import get_logger

logger = get_logger("tampering_evidence")

class TamperingEvidenceBuilder:
    """Builds structured common EvidenceItem objects and explainable audit reasons."""

    @classmethod
    def build_evidence(
        cls,
        confidence: float,
        risk_level: str,
        tampering_detected: bool,
        suspicious_regions: List[SuspiciousRegion],
        correlations: List[Dict[str, Any]],
        model_name: str
    ) -> Tuple[List[EvidenceItem], List[str]]:
        """
        Returns a tuple of (List[EvidenceItem], List[explainable_reasons_strings]).
        Only reports evidence actually supported by detector output.
        """
        evidence_items: List[EvidenceItem] = []
        reasons: List[str] = []

        if not tampering_detected:
            reasons.append(f"Image signal analysis verified document visual continuity (Confidence: {confidence:.2f})")
            return evidence_items, reasons

        # Severity mapping based on risk level
        if risk_level == "HIGH":
            sev = SeverityLevel.HIGH
        elif risk_level == "MEDIUM":
            sev = SeverityLevel.MEDIUM
        else:
            sev = SeverityLevel.LOW

        # 1. Evidence items for OCR field overlaps
        if correlations:
            for corr in correlations:
                desc = corr.get("description", "Suspicious region detected over document field")
                reasons.append(desc)

                bbox_list = None
                reg_id = corr.get("region_id")
                target_reg = next((r for r in suspicious_regions if r.region_id == reg_id), None)
                if target_reg and target_reg.bounding_box:
                    bx = target_reg.bounding_box
                    bbox_list = [bx.x, bx.y, bx.x + bx.width, bx.y + bx.height]

                evidence_items.append(EvidenceItem(
                    source_module="TAMPERING_AI",
                    data={
                        "rule_id": "TAMPER_HEATMAP_FIELD_OVERLAP",
                        "field": corr.get("field_name"),
                        "field_label": corr.get("field_label"),
                        "anomaly_type": corr.get("anomaly_type"),
                        "overlap_ratio": corr.get("overlap_ratio", 0.0),
                        "description": desc
                    },
                    confidence=confidence,
                    strength=0.90,
                    severity=sev,
                    provenance=f"tampering:{model_name.lower()}",
                    bbox=bbox_list,
                    reason_code="TAMPERING_FIELD_OVERLAP"
                ))

        # 2. Evidence items for general suspicious bounding regions
        if suspicious_regions and not correlations:
            desc = f"{len(suspicious_regions)} localized visual anomaly region(s) detected in document layout"
            reasons.append(desc)
            
            first_bx = suspicious_regions[0].bounding_box
            bbox_list = [first_bx.x, first_bx.y, first_bx.x + first_bx.width, first_bx.y + first_bx.height] if first_bx else None

            evidence_items.append(EvidenceItem(
                source_module="TAMPERING_AI",
                data={
                    "rule_id": "TAMPER_LOCAL_ANOMALY",
                    "regions_count": len(suspicious_regions),
                    "description": desc
                },
                confidence=confidence,
                strength=0.85,
                severity=sev,
                provenance=f"tampering:{model_name.lower()}",
                bbox=bbox_list,
                reason_code="TAMPERING_LOCAL_ANOMALY"
            ))

        # 3. Model Confidence Summary Item & Reason
        conf_reason = f"Image tampering model confidence: {confidence:.2f} (Risk: {risk_level})"
        reasons.append(conf_reason)

        evidence_items.append(EvidenceItem(
            source_module="TAMPERING_AI",
            data={
                "rule_id": "TAMPER_MODEL_CONFIDENCE",
                "model": model_name,
                "confidence": confidence,
                "risk_level": risk_level,
                "description": conf_reason
            },
            confidence=confidence,
            strength=0.95,
            severity=sev,
            provenance=f"tampering:{model_name.lower()}",
            reason_code="TAMPERING_MODEL_SCORE"
        ))

        return evidence_items, reasons
