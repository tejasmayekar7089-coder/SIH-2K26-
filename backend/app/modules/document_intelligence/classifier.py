from abc import ABC, abstractmethod
import re
from typing import Tuple, Optional
import numpy as np

from app.schemas.document import DocumentCategory
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.core.logging import get_logger

logger = get_logger("document_classifier")

class BaseDocumentClassifier(ABC):
    """Abstract base class for document type classification."""

    @abstractmethod
    def classify(self, ocr_result: OCRResult, image_rgb: Optional[np.ndarray] = None) -> Tuple[DocumentCategory, float]:
        """Classify document and return (DocumentCategory, confidence_score)."""
        pass

class HeuristicDocumentClassifier(BaseDocumentClassifier):
    """
    Deterministic heuristic classifier using keyword matching, regex patterns,
    and structural markers to identify document categories.
    """

    # Keyword rules with associated weights
    PASSPORT_KEYWORDS = [
        ("PASSPORT", 0.4),
        ("REPUBLIC OF INDIA", 0.4),
        ("P<IND", 0.6),
        ("PASSPORT NO", 0.3),
        ("SURNAME", 0.15),
        ("GIVEN NAMES", 0.15),
        ("NATIONALITY", 0.15)
    ]

    AADHAAR_KEYWORDS = [
        ("UNIQUE IDENTIFICATION AUTHORITY OF INDIA", 0.5),
        ("GOVERNMENT OF INDIA", 0.3),
        ("AADHAAR", 0.4),
        ("AADHAR", 0.4),
        ("MERA AADHAAR", 0.4),
        ("ENROLLMENT NO", 0.3),
        ("HELP@UIDAI.GOV.IN", 0.4),
        ("HELP LINE", 0.2),
        ("UIDAI", 0.4)
    ]

    DRIVING_LICENCE_KEYWORDS = [
        ("DRIVING LICENCE", 0.5),
        ("DRIVING LICENSE", 0.5),
        ("UNION OF INDIA", 0.3),
        ("DRIVING", 0.2),
        ("LICENCE NO", 0.4),
        ("LICENSE NO", 0.4),
        ("DL NO", 0.4),
        ("AUTHORISATION TO DRIVE", 0.4),
        ("TRANSPORT", 0.2),
        ("FORM 7", 0.3),
        ("MOTOR VEHICLE", 0.3)
    ]

    # Regex patterns
    AADHAAR_NUMBER_PATTERN = re.compile(r'\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b')
    PASSPORT_NUMBER_PATTERN = re.compile(r'\b[A-PR-WYa-pr-wy]\d{7}\b')
    PASSPORT_MRZ_PATTERN = re.compile(r'P[A-Z0-9<]{43}')
    DL_NUMBER_PATTERN = re.compile(r'\b[A-Z]{2}[-\s]?\d{2}[-\s]?\d{4,11}\b', re.IGNORECASE)

    def classify(self, ocr_result: OCRResult, image_rgb: Optional[np.ndarray] = None) -> Tuple[DocumentCategory, float]:
        """Classify document based on OCR text and regex patterns."""
        if not ocr_result or not ocr_result.full_text.strip():
            logger.info("Empty OCR text provided to classifier. Classifying as UNKNOWN.")
            return DocumentCategory.UNKNOWN, 0.0

        raw_text_upper = ocr_result.full_text.upper()

        passport_score = 0.0
        aadhaar_score = 0.0
        dl_score = 0.0

        # 1. Keyword matching
        for kw, weight in self.PASSPORT_KEYWORDS:
            if kw in raw_text_upper:
                passport_score += weight

        for kw, weight in self.AADHAAR_KEYWORDS:
            if kw in raw_text_upper:
                aadhaar_score += weight

        for kw, weight in self.DRIVING_LICENCE_KEYWORDS:
            if kw in raw_text_upper:
                dl_score += weight

        # 2. Regex pattern checks
        if self.PASSPORT_MRZ_PATTERN.search(raw_text_upper):
            passport_score += 0.5
        elif self.PASSPORT_NUMBER_PATTERN.search(raw_text_upper) and ("IND" in raw_text_upper or "PASSPORT" in raw_text_upper):
            passport_score += 0.3

        if self.AADHAAR_NUMBER_PATTERN.search(raw_text_upper):
            aadhaar_score += 0.5

        if self.DL_NUMBER_PATTERN.search(raw_text_upper) and ("LICENCE" in raw_text_upper or "LICENSE" in raw_text_upper or "DL" in raw_text_upper):
            dl_score += 0.4

        # Normalize confidence cap at 0.99
        passport_confidence = min(0.99, passport_score)
        aadhaar_confidence = min(0.99, aadhaar_score)
        dl_confidence = min(0.99, dl_score)

        scores = [
            (DocumentCategory.PASSPORT, passport_confidence),
            (DocumentCategory.AADHAAR, aadhaar_confidence),
            (DocumentCategory.DRIVING_LICENSE, dl_confidence)
        ]

        # Sort by confidence descending
        scores.sort(key=lambda x: x[1], reverse=True)
        top_category, top_confidence = scores[0]

        # Minimum threshold to avoid false positive classification
        if top_confidence >= 0.35:
            logger.info(f"Classified document as {top_category.value} with confidence {top_confidence:.2f}")
            return top_category, round(top_confidence, 2)

        logger.info("Document did not match any classification threshold. Classifying as UNKNOWN.")
        return DocumentCategory.UNKNOWN, 0.0
