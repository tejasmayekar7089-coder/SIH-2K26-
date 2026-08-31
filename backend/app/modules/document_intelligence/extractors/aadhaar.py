import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.document import DocumentCategory
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRResult, OCRItem
from app.modules.document_intelligence.extractors.base import BaseFieldExtractor
from app.core.logging import get_logger

logger = get_logger("aadhaar_extractor")

# Verhoeff Multiplication Table (d)
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# Verhoeff Permutation Table (p)
VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 4, 9, 0],
    [2, 6, 8, 7, 5, 0, 1, 3, 4, 9],
    [3, 7, 1, 9, 5, 2, 8, 0, 4, 6],
    [4, 8, 0, 1, 6, 3, 7, 9, 2, 5],
    [5, 9, 8, 6, 7, 0, 4, 1, 3, 2],
    [6, 0, 9, 5, 8, 1, 7, 2, 3, 4],
    [7, 1, 4, 0, 9, 2, 8, 3, 5, 6]
]

def verhoeff_validate(number_str: str) -> bool:
    """Validates a 12-digit Aadhaar number using the Verhoeff checksum algorithm."""
    digits = [int(c) for c in number_str if c.isdigit()]
    if len(digits) != 12:
        return False
    c = 0
    for i, item in enumerate(reversed(digits)):
        c = VERHOEFF_D[c][VERHOEFF_P[i % 8][item]]
    return c == 0

def mask_aadhaar_number(raw_num: str) -> str:
    """Privacy helper: Mask Aadhaar number for log output (e.g. XXXX-XXXX-1234)."""
    digits = re.sub(r'\D', '', str(raw_num))
    if len(digits) == 12:
        return f"XXXX-XXXX-{digits[-4:]}"
    elif len(digits) >= 4:
        return f"XXXX-XXXX-{digits[-4:]}"
    return "XXXX-XXXX-XXXX"

class AadhaarFieldExtractor(BaseFieldExtractor):
    """Layout-agnostic field extractor for Aadhaar cards with Verhoeff validation and privacy safeguards."""

    AADHAAR_NUM_RE = re.compile(r'\b([2-9]\d{3}\s?\d{4}\s?\d{4})\b')
    RAW_12_DIGIT_RE = re.compile(r'\b([2-9]\d{11})\b')
    DOB_LABEL_RE = re.compile(r'(?:DOB|D\.O\.B|DATE OF BIRTH|YEAR OF BIRTH|YOB)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4}|\d{4})', re.IGNORECASE)
    STANDALONE_DATE_RE = re.compile(r'\b(\d{2}[/\-.]\d{2}[/\-.]\d{4}|\d{4})\b')
    GENDER_RE = re.compile(r'\b(MALE|FEMALE|TRANSGENDER|M|F)\b', re.IGNORECASE)
    PINCODE_RE = re.compile(r'\b([1-9]\d{5})\b')
    ADDRESS_ANCHOR_RE = re.compile(r'(?:ADDRESS|S/O|W/O|D/O|C/O|CARE OF)[:\s]*', re.IGNORECASE)

    IGNORED_NAME_PATTERNS = [
        "GOVERNMENT OF INDIA", "BHARAT SARKAR", "UNIQUE IDENTIFICATION",
        "AUTHORITY OF INDIA", "MERA AADHAAR", "UIDAI", "ENROLLMENT",
        "HELP", "ADDRESS", "DOB", "MALE", "FEMALE", "ISSUE", "VID"
    ]

    def extract_fields(self, ocr_result: OCRResult) -> ExtractionResult:
        logger.info("Executing layout-agnostic Aadhaar field extraction...")

        full_name: Optional[ExtractedField] = None
        date_of_birth: Optional[ExtractedField] = None
        document_number: Optional[ExtractedField] = None
        gender: Optional[ExtractedField] = None
        address: Optional[ExtractedField] = None
        additional: Dict[str, ExtractedField] = {}

        if not ocr_result or not ocr_result.items:
            logger.warning("Empty OCR result supplied to AadhaarFieldExtractor.")
            return ExtractionResult(
                document_category=DocumentCategory.AADHAAR,
                category_confidence=0.95,
                raw_text="",
                ocr_confidence_mean=0.0
            )

        # 1. Aadhaar Number Extraction & Verhoeff Checksum Validation
        doc_num_item, num_val, is_verhoeff_valid = self._extract_aadhaar_number(ocr_result)
        if doc_num_item and num_val:
            masked_log_num = mask_aadhaar_number(num_val)
            logger.info(f"Extracted Aadhaar Number candidate: {masked_log_num} (Verhoeff Valid: {is_verhoeff_valid})")
            provenance_tag = "ocr:verhoeff_checksum_matched" if is_verhoeff_valid else "ocr:regex_pattern_matched"
            document_number = ExtractedField(
                field_name="aadhaar_number",
                value=num_val,
                confidence=doc_num_item.confidence,
                bounding_box=doc_num_item.bounding_box,
                source=ocr_result.engine_name,
                provenance=provenance_tag
            )

        # 2. Date of Birth Extraction & Plausibility Validation
        dob_item, dob_str, is_dob_plausible = self._extract_date_of_birth(ocr_result)
        if dob_item and dob_str:
            logger.info(f"Extracted Date of Birth: {dob_str} (Plausible: {is_dob_plausible})")
            date_of_birth = ExtractedField(
                field_name="date_of_birth",
                value=dob_str,
                confidence=dob_item.confidence,
                bounding_box=dob_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:dob_label_matched" if "DOB" in dob_item.text.upper() else "ocr:date_pattern_matched"
            )

        # 3. Gender Extraction & Normalization
        gender_item, normalized_gender = self._extract_gender(ocr_result)
        if gender_item and normalized_gender:
            logger.info(f"Extracted Normalized Gender: {normalized_gender}")
            gender = ExtractedField(
                field_name="gender",
                value=normalized_gender,
                confidence=gender_item.confidence,
                bounding_box=gender_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:gender_keyword_matched"
            )

        # 4. Name Extraction (Spatial & Text Heading Heuristics)
        name_item, name_val = self._extract_name(ocr_result, dob_item, doc_num_item)
        if name_item and name_val:
            logger.info(f"Extracted Full Name: {name_val}")
            full_name = ExtractedField(
                field_name="name",
                value=name_val,
                confidence=name_item.confidence,
                bounding_box=name_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:spatial_heading_heuristic"
            )

        # 5. Address Extraction (Anchor Label & Pincode Cluster Heuristics)
        addr_item, addr_text, bbox_addr = self._extract_address(ocr_result)
        if addr_text:
            logger.info(f"Extracted Address block (length: {len(addr_text)} chars)")
            address = ExtractedField(
                field_name="address",
                value=addr_text,
                confidence=addr_item.confidence if addr_item else 0.90,
                bounding_box=bbox_addr,
                source=ocr_result.engine_name,
                provenance="ocr:address_anchor_spatial_cluster"
            )

        # 6. Validation Summary Metadata
        validation_info = self._build_validation_summary(
            document_number=document_number,
            name=full_name,
            date_of_birth=date_of_birth,
            gender=gender,
            address=address,
            is_verhoeff_valid=is_verhoeff_valid,
            is_dob_plausible=is_dob_plausible
        )

        additional["validation_summary"] = ExtractedField(
            field_name="validation_summary",
            value=validation_info["summary_text"],
            confidence=1.0,
            source="aadhaar_validator",
            provenance="deterministic_rule_engine"
        )

        return ExtractionResult(
            document_category=DocumentCategory.AADHAAR,
            category_confidence=0.98,
            full_name=full_name,
            date_of_birth=date_of_birth,
            document_number=document_number,
            nationality=ExtractedField(field_name="nationality", value="IND", confidence=0.99, source=ocr_result.engine_name, provenance="ocr:default_jurisdiction"),
            gender=gender,
            address=address,
            additional_fields=additional,
            raw_text=ocr_result.full_text,
            ocr_confidence_mean=ocr_result.mean_confidence
        )

    def _extract_aadhaar_number(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str], bool]:
        """Scans items for 12-digit Aadhaar number pattern and validates via Verhoeff algorithm."""
        best_item = None
        best_num = None
        best_verhoeff = False

        for item in ocr_result.items:
            m = self.AADHAAR_NUM_RE.search(item.text)
            if not m:
                m = self.RAW_12_DIGIT_RE.search(item.text.replace(" ", ""))

            if m:
                raw_digits = re.sub(r'\D', '', m.group(1))
                if len(raw_digits) == 12:
                    formatted_num = f"{raw_digits[:4]} {raw_digits[4:8]} {raw_digits[8:]}"
                    is_valid = verhoeff_validate(raw_digits)
                    if is_valid:
                        return item, formatted_num, True
                    # Store as backup if Verhoeff fails
                    if not best_num:
                        best_item = item
                        best_num = formatted_num
                        best_verhoeff = False

        return best_item, best_num, best_verhoeff

    def _extract_date_of_birth(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str], bool]:
        """Extracts date of birth or year of birth with plausibility check."""
        for idx, item in enumerate(ocr_result.items):
            m = self.DOB_LABEL_RE.search(item.text)
            if m:
                raw_date = m.group(1).strip()
                norm_date, is_plausible = self._normalize_and_validate_date(raw_date)
                return item, norm_date, is_plausible

            if "DOB" in item.text.upper() or "YEAR OF BIRTH" in item.text.upper() or "YOB" in item.text.upper():
                # Check next item in sequence
                if idx + 1 < len(ocr_result.items):
                    next_item = ocr_result.items[idx + 1]
                    m_next = self.STANDALONE_DATE_RE.search(next_item.text)
                    if m_next:
                        raw_date = m_next.group(1).strip()
                        norm_date, is_plausible = self._normalize_and_validate_date(raw_date)
                        return next_item, norm_date, is_plausible

        # Fallback regex scan for standalone date
        for item in ocr_result.items:
            if not self.AADHAAR_NUM_RE.search(item.text):
                m_standalone = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', item.text)
                if m_standalone:
                    raw_date = m_standalone.group(1)
                    norm_date, is_plausible = self._normalize_and_validate_date(raw_date)
                    return item, norm_date, is_plausible

        return None, None, False

    def _normalize_and_validate_date(self, raw_date_str: str) -> Tuple[str, bool]:
        """Normalizes date string to YYYY-MM-DD or YYYY and checks plausibility."""
        current_year = datetime.now().year
        # Handle 4-digit YOB
        if len(raw_date_str) == 4 and raw_date_str.isdigit():
            yob = int(raw_date_str)
            is_plausible = 1900 <= yob <= current_year
            return raw_date_str, is_plausible

        # Handle DD/MM/YYYY or DD-MM-YYYY
        parts = re.split(r'[/\-.]', raw_date_str)
        if len(parts) == 3:
            try:
                if len(parts[2]) == 4:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                elif len(parts[0]) == 4:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    return raw_date_str, False

                is_plausible = (1900 <= year <= current_year) and (1 <= month <= 12) and (1 <= day <= 31)
                normalized = f"{year:04d}-{month:02d}-{day:02d}"
                return normalized, is_plausible
            except ValueError:
                pass

        return raw_date_str, False

    def _extract_gender(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str]]:
        """Extracts and normalizes gender to MALE, FEMALE, or TRANSGENDER."""
        for item in ocr_result.items:
            txt = item.text.upper()
            if "FEMALE" in txt or "/ FEMALE" in txt or "SEX: F" in txt:
                return item, "FEMALE"
            elif "MALE" in txt or "/ MALE" in txt or "SEX: M" in txt:
                return item, "MALE"
            elif "TRANSGENDER" in txt:
                return item, "TRANSGENDER"

        return None, None

    def _extract_name(self, ocr_result: OCRResult, dob_item: Optional[OCRItem], doc_num_item: Optional[OCRItem]) -> Tuple[Optional[OCRItem], Optional[str]]:
        """Extracts full name using spatial layout and exclusion rules."""
        dob_y = dob_item.bounding_box.y if dob_item and dob_item.bounding_box else 99999
        num_y = doc_num_item.bounding_box.y if doc_num_item and doc_num_item.bounding_box else 99999

        candidates = []
        for item in ocr_result.items:
            txt_upper = item.text.upper().strip()

            # Ignore headers, aadhaar numbers, DOB, gender, address
            if any(pattern in txt_upper for pattern in self.IGNORED_NAME_PATTERNS):
                continue
            if self.AADHAAR_NUM_RE.search(txt_upper) or self.RAW_12_DIGIT_RE.search(txt_upper):
                continue

            # Must be positioned above DOB or Aadhaar Number line if available
            if item.bounding_box:
                if item.bounding_box.y >= dob_y or item.bounding_box.y >= num_y:
                    continue

            # Alphabetic text check
            clean_name = re.sub(r'[^A-Z\s.]', '', txt_upper).strip()
            words = clean_name.split()
            if 1 <= len(words) <= 4 and len(clean_name) >= 3:
                candidates.append((item, clean_name))

        if candidates:
            # Select candidate with highest confidence or earliest Y position
            candidates.sort(key=lambda c: (c[0].bounding_box.y if c[0].bounding_box else 0, -c[0].confidence))
            best_item, name_str = candidates[0]
            return best_item, name_str.title()

        return None, None

    def _extract_address(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str], Optional[BoundingBox]]:
        """Extracts multi-line address using Address: / S/O / W/O anchors and pincode regex."""
        address_items = []
        anchor_found = False

        for idx, item in enumerate(ocr_result.items):
            txt = item.text.strip()
            if self.ADDRESS_ANCHOR_RE.search(txt) or anchor_found:
                anchor_found = True
                # Exclude lines that are Aadhaar numbers
                if not self.AADHAAR_NUM_RE.search(txt) and "GOVERNMENT OF INDIA" not in txt.upper():
                    clean_line = re.sub(r'^(?:ADDRESS|S/O|W/O|D/O|C/O|CARE OF)[:\s]*', '', txt, flags=re.IGNORECASE).strip()
                    if clean_line:
                        address_items.append(item)
                if self.PINCODE_RE.search(txt):
                    # Stop after pincode line is reached
                    break

        if not address_items:
            # Fallback: look for items around pincode
            for idx, item in enumerate(ocr_result.items):
                if self.PINCODE_RE.search(item.text):
                    # Take up to 3 preceding items as address
                    start_idx = max(0, idx - 3)
                    address_items = [ocr_result.items[i] for i in range(start_idx, idx + 1) if "GOVERNMENT" not in ocr_result.items[i].text.upper()]
                    break

        if address_items:
            full_address_str = ", ".join([it.text.strip() for it in address_items])
            primary_item = address_items[0]

            # Merge bounding box across all address items
            xs = [it.bounding_box.x for it in address_items if it.bounding_box]
            ys = [it.bounding_box.y for it in address_items if it.bounding_box]
            x2s = [it.bounding_box.x + it.bounding_box.width for it in address_items if it.bounding_box]
            y2s = [it.bounding_box.y + it.bounding_box.height for it in address_items if it.bounding_box]

            if xs and ys and x2s and y2s:
                merged_bbox = BoundingBox(
                    x=min(xs),
                    y=min(ys),
                    width=max(x2s) - min(xs),
                    height=max(y2s) - min(ys)
                )
            else:
                merged_bbox = primary_item.bounding_box

            return primary_item, full_address_str, merged_bbox

        return None, None, None

    def _build_validation_summary(self,
                                  document_number: Optional[ExtractedField],
                                  name: Optional[ExtractedField],
                                  date_of_birth: Optional[ExtractedField],
                                  gender: Optional[ExtractedField],
                                  address: Optional[ExtractedField],
                                  is_verhoeff_valid: bool,
                                  is_dob_plausible: bool) -> Dict[str, Any]:
        """Builds validation metadata flags without making unverified authenticity claims."""
        extracted_keys = []
        missing_keys = []

        for field_key, field_obj in [("aadhaar_number", document_number), ("name", name), ("date_of_birth", date_of_birth), ("gender", gender), ("address", address)]:
            if field_obj and field_obj.value:
                extracted_keys.append(field_key)
            else:
                missing_keys.append(field_key)

        summary_text = (
            f"Extracted {len(extracted_keys)}/5 fields. "
            f"Verhoeff Checksum: {'VALID' if is_verhoeff_valid else 'INVALID/UNVERIFIED'}. "
            f"DOB Plausible: {'YES' if is_dob_plausible else 'NO'}. "
            f"Disclaimer: Formatting checks DO NOT constitute government database verification."
        )

        return {
            "required_fields_present": extracted_keys,
            "missing_required_fields": missing_keys,
            "is_aadhaar_number_valid": is_verhoeff_valid,
            "is_dob_plausible": is_dob_plausible,
            "is_gender_normalized": gender is not None,
            "summary_text": summary_text
        }
