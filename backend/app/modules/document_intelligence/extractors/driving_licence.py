import re
from datetime import datetime
from typing import Optional, Dict, List, Tuple, Any
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.document import DocumentCategory
from app.schemas.common import BoundingBox
from app.modules.document_intelligence.ocr.schemas import OCRResult, OCRItem
from app.modules.document_intelligence.extractors.base import BaseFieldExtractor
from app.core.logging import get_logger

logger = get_logger("dl_extractor")

VALID_INDIAN_STATE_CODES = {
    "MH", "DL", "KA", "TN", "UP", "GJ", "RJ", "TS", "AP", "KL",
    "WB", "HR", "PB", "MP", "OR", "AS", "BR", "CG", "GA", "HP",
    "JH", "JK", "ML", "MN", "MZ", "NL", "SK", "TR", "UK", "UT",
    "AN", "CH", "DN", "DD", "LD", "PY"
}

KNOWN_VEHICLE_CLASSES = {
    "MCWG", "MCWOG", "MCOAG", "LMV", "LMV-NT", "TRANS", "TR",
    "3WNT", "3W-CAB", "LDRXCV", "HGMV", "HPMV", "ALT"
}

class DrivingLicenceFieldExtractor(BaseFieldExtractor):
    """
    Layout-agnostic field extractor for Indian Driving Licences across all state RTOs.
    Parses DL Number, Name, DOB, Issue Date, Expiry Date, Address, Vehicle Classes (COV), and Issuing Authority.
    """

    # Regex patterns
    DL_NUM_STRICT_RE = re.compile(r'\b([A-Z]{2}[-\s/]?\d{2}[-\s/]?(?:19|20)\d{2}[-\s/]?\d{4,7}|\b[A-Z]{2}\d{13,15}\b)', re.IGNORECASE)
    DL_NUM_GENERIC_RE = re.compile(r'(?:DL\s*NO|LICENCE\s*NO|LICENSE\s*NO|NO)[:\s]*([A-Z]{2}[-\s/0-9]{10,18})', re.IGNORECASE)
    
    DOB_RE = re.compile(r'(?:DOB|D\.O\.B|DATE OF BIRTH)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    ISSUE_RE = re.compile(r'(?:ISSUE\s*DATE|DATE OF ISSUE|ISSUE|DOI|VALID FROM|ISSUED ON)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    EXPIRY_RE = re.compile(r'(?:EXPIRY\s*DATE|DATE OF EXPIRY|EXPIRY|DOE|VALID TILL|VALID UNTIL|NT VALID TILL)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    
    ADDRESS_ANCHOR_RE = re.compile(r'(?:ADDRESS|ADD|PERM ADD|S/O|W/O|D/O|SON OF|WIFE OF)[:\s]*', re.IGNORECASE)
    PINCODE_RE = re.compile(r'\b([1-9]\d{5})\b')
    COV_ANCHOR_RE = re.compile(r'(?:COV|CLASS OF VEHICLE|AUTHORISATION TO DRIVE|CATEGORY)[:\s]*', re.IGNORECASE)
    RTO_ANCHOR_RE = re.compile(r'(?:ISSUING AUTHORITY|LICENSING AUTHORITY|RTO|R\.T\.O|ISSUED BY)[:\s]*', re.IGNORECASE)

    IGNORED_NAME_WORDS = [
        "UNION OF INDIA", "INDIAN UNION", "DRIVING LICENCE", "DRIVING LICENSE",
        "TRANSPORT DEPARTMENT", "MOTOR VEHICLES", "FORM 7", "DL NO", "LICENCE NO",
        "ADDRESS", "AUTHORITY", "VALIDITY", "CLASS OF VEHICLE", "COV", "ISSUE",
        "EXPIRY", "VALID TILL", "VALID FROM", "DATE"
    ]

    def extract_fields(self, ocr_result: OCRResult) -> ExtractionResult:
        logger.info("Executing layout-agnostic Driving Licence field extraction...")

        full_name: Optional[ExtractedField] = None
        date_of_birth: Optional[ExtractedField] = None
        document_number: Optional[ExtractedField] = None
        issue_date: Optional[ExtractedField] = None
        expiry_date: Optional[ExtractedField] = None
        address: Optional[ExtractedField] = None
        additional: Dict[str, ExtractedField] = {}

        if not ocr_result or not ocr_result.items:
            logger.warning("Empty OCR result supplied to DrivingLicenceFieldExtractor.")
            return ExtractionResult(
                document_category=DocumentCategory.DRIVING_LICENSE,
                category_confidence=0.95,
                raw_text="",
                ocr_confidence_mean=0.0
            )

        # 1. Driving Licence Number Extraction & Format Validation
        dl_item, dl_val, is_dl_format_valid = self._extract_dl_number(ocr_result)
        if dl_item and dl_val:
            logger.info(f"Extracted DL Number: {dl_val} (Valid Format: {is_dl_format_valid})")
            document_number = ExtractedField(
                field_name="driving_licence_number",
                value=dl_val,
                confidence=dl_item.confidence,
                bounding_box=dl_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:state_rto_format_matched" if is_dl_format_valid else "ocr:regex_dl_pattern",
                severity="LOW" if is_dl_format_valid else "MEDIUM"
            )

        # 2. Date of Birth Extraction & Plausibility Check
        dob_item, dob_val, is_dob_plausible = self._extract_dob(ocr_result)
        if dob_item and dob_val:
            logger.info(f"Extracted Date of Birth: {dob_val} (Plausible: {is_dob_plausible})")
            date_of_birth = ExtractedField(
                field_name="date_of_birth",
                value=dob_val,
                confidence=dob_item.confidence,
                bounding_box=dob_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:dob_label_matched",
                severity="LOW" if is_dob_plausible else "MEDIUM"
            )

        # 3. Issue Date & Expiry Date Extraction
        iss_item, iss_val = self._extract_date_by_pattern(ocr_result, self.ISSUE_RE)
        if iss_item and iss_val:
            logger.info(f"Extracted Date of Issue: {iss_val}")
            issue_date = ExtractedField(
                field_name="date_of_issue",
                value=iss_val,
                confidence=iss_item.confidence,
                bounding_box=iss_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:issue_date_label_matched",
                severity="LOW"
            )

        exp_item, exp_val = self._extract_date_by_pattern(ocr_result, self.EXPIRY_RE)
        if exp_item and exp_val:
            logger.info(f"Extracted Expiry Date: {exp_val}")
            expiry_date = ExtractedField(
                field_name="validity_expiry_date",
                value=exp_val,
                confidence=exp_item.confidence,
                bounding_box=exp_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:expiry_date_label_matched",
                severity="LOW"
            )

        # Chronology Validation: issue_date < expiry_date
        is_chronology_valid = self._validate_date_chronology(issue_date, expiry_date)
        if not is_chronology_valid and expiry_date:
            logger.warning("Chronological anomaly detected: Date of Issue is on or after Expiry Date!")
            expiry_date.severity = "HIGH"
            expiry_date.provenance = "ocr:chronology_anomaly_invalid_dates"

        # 4. Name Extraction (Anchor & Spatial Heuristics)
        name_item, name_val = self._extract_name(ocr_result, dob_item, dl_item)
        if name_item and name_val:
            logger.info(f"Extracted Licence Holder Name: {name_val}")
            full_name = ExtractedField(
                field_name="name",
                value=name_val,
                confidence=name_item.confidence,
                bounding_box=name_item.bounding_box,
                source=ocr_result.engine_name,
                provenance="ocr:name_anchor_spatial_heuristic",
                severity="LOW"
            )

        # 5. Address Extraction
        addr_item, addr_text, addr_bbox = self._extract_address(ocr_result)
        if addr_text:
            logger.info(f"Extracted Address block ({len(addr_text)} chars)")
            address = ExtractedField(
                field_name="address",
                value=addr_text,
                confidence=addr_item.confidence if addr_item else 0.90,
                bounding_box=addr_bbox,
                source=ocr_result.engine_name,
                provenance="ocr:address_anchor_spatial_cluster",
                severity="LOW"
            )

        # 6. Vehicle Class (COV) Categories Extraction
        cov_item, cov_val = self._extract_vehicle_classes(ocr_result)
        if cov_val:
            logger.info(f"Extracted Vehicle Classes: {cov_val}")
            additional["vehicle_classes"] = ExtractedField(
                field_name="vehicle_class_categories",
                value=cov_val,
                confidence=cov_item.confidence if cov_item else 0.92,
                bounding_box=cov_item.bounding_box if cov_item else None,
                source=ocr_result.engine_name,
                provenance="ocr:cov_keyword_spatial_cluster",
                severity="LOW"
            )

        # 7. Issuing Authority / RTO Extraction
        rto_item, rto_val = self._extract_issuing_authority(ocr_result)
        if rto_val:
            logger.info(f"Extracted Issuing Authority: {rto_val}")
            additional["issuing_authority"] = ExtractedField(
                field_name="issuing_authority",
                value=rto_val,
                confidence=rto_item.confidence if rto_item else 0.90,
                bounding_box=rto_item.bounding_box if rto_item else None,
                source=ocr_result.engine_name,
                provenance="ocr:rto_authority_anchor_matched",
                severity="LOW"
            )

        # 8. Validation Summary
        val_summary = self._build_validation_summary(
            dl_number=document_number,
            name=full_name,
            dob=date_of_birth,
            issue_date=issue_date,
            expiry_date=expiry_date,
            is_dl_format_valid=is_dl_format_valid,
            is_chronology_valid=is_chronology_valid
        )

        additional["validation_summary"] = ExtractedField(
            field_name="validation_summary",
            value=val_summary["summary_text"],
            confidence=1.0,
            source="dl_validator",
            provenance="deterministic_rule_engine",
            severity="LOW" if is_chronology_valid and is_dl_format_valid else "HIGH"
        )

        return ExtractionResult(
            document_category=DocumentCategory.DRIVING_LICENSE,
            category_confidence=0.98,
            full_name=full_name,
            date_of_birth=date_of_birth,
            document_number=document_number,
            nationality=ExtractedField(field_name="nationality", value="IND", confidence=0.99, source=ocr_result.engine_name, provenance="ocr:default_jurisdiction"),
            issue_date=issue_date,
            expiry_date=expiry_date,
            address=address,
            additional_fields=additional,
            raw_text=ocr_result.full_text,
            ocr_confidence_mean=ocr_result.mean_confidence
        )

    def _extract_dl_number(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str], bool]:
        """Extracts Driving Licence Number and checks Indian state RTO prefix."""
        for item in ocr_result.items:
            m = self.DL_NUM_STRICT_RE.search(item.text)
            if m:
                raw_val = m.group(1).strip().upper()
                clean_val = re.sub(r'[\s/]', '-', raw_val)
                state_code = clean_val[:2]
                is_valid_format = state_code in VALID_INDIAN_STATE_CODES
                return item, clean_val, is_valid_format

            m2 = self.DL_NUM_GENERIC_RE.search(item.text)
            if m2:
                raw_val = m2.group(1).strip().upper()
                clean_val = re.sub(r'[\s/]', '-', raw_val)
                state_code = clean_val[:2]
                is_valid_format = state_code in VALID_INDIAN_STATE_CODES
                return item, clean_val, is_valid_format

        return None, None, False

    def _extract_dob(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str], bool]:
        """Extracts Date of Birth with plausibility verification."""
        for item in ocr_result.items:
            m = self.DOB_RE.search(item.text)
            if m:
                raw_date = m.group(1).strip()
                norm_date, is_plausible = self._normalize_date(raw_date)
                return item, norm_date, is_plausible
        return None, None, False

    def _extract_date_by_pattern(self, ocr_result: OCRResult, pattern: re.Pattern) -> Tuple[Optional[OCRItem], Optional[str]]:
        """Extracts date using provided regex pattern."""
        for item in ocr_result.items:
            m = pattern.search(item.text)
            if m:
                raw_date = m.group(1).strip()
                norm_date, _ = self._normalize_date(raw_date)
                return item, norm_date
        return None, None

    def _normalize_date(self, date_str: str) -> Tuple[str, bool]:
        """Normalizes date string to YYYY-MM-DD format."""
        current_year = datetime.now().year
        parts = re.split(r'[/\-.]', date_str)
        if len(parts) == 3:
            try:
                if len(parts[2]) == 4:
                    day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
                elif len(parts[0]) == 4:
                    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
                else:
                    return date_str, False

                is_plausible = (1900 <= year <= current_year + 30) and (1 <= month <= 12) and (1 <= day <= 31)
                normalized = f"{year:04d}-{month:02d}-{day:02d}"
                return normalized, is_plausible
            except ValueError:
                pass
        return date_str, False

    def _validate_date_chronology(self, issue_date: Optional[ExtractedField], expiry_date: Optional[ExtractedField]) -> bool:
        """Validates that issue_date < expiry_date."""
        if not issue_date or not expiry_date:
            return True
        try:
            d_iss = datetime.strptime(issue_date.value, "%Y-%m-%d")
            d_exp = datetime.strptime(expiry_date.value, "%Y-%m-%d")
            return d_iss < d_exp
        except ValueError:
            return True

    def _extract_name(self, ocr_result: OCRResult, dob_item: Optional[OCRItem], dl_item: Optional[OCRItem]) -> Tuple[Optional[OCRItem], Optional[str]]:
        """Extracts Licence Holder Name using anchors and exclusion heuristics."""
        for idx, item in enumerate(ocr_result.items):
            txt_upper = item.text.upper()
            if ("NAME" in txt_upper or "HOLDER" in txt_upper) and "FATHER" not in txt_upper and "HUSBAND" not in txt_upper and "LICENCE" not in txt_upper and "LICENSE" not in txt_upper and "SURNAME" not in txt_upper:
                clean_val = re.sub(r'^(?:NAME|HOLDER|NAME OF HOLDER|LICENCE HOLDER)[:\s]*', '', txt_upper).strip()
                clean_name = re.sub(r'[^A-Z\s.]', '', clean_val).strip()
                if len(clean_name) >= 3 and not any(ig in clean_name for ig in self.IGNORED_NAME_WORDS):
                    return item, clean_name.title()
                elif idx + 1 < len(ocr_result.items):
                    next_item = ocr_result.items[idx + 1]
                    next_name = re.sub(r'[^A-Z\s.]', '', next_item.text.upper()).strip()
                    if len(next_name) >= 3 and not any(ig in next_name for ig in self.IGNORED_NAME_WORDS):
                        return next_item, next_name.title()

        # Positional fallback
        candidates = []
        for item in ocr_result.items:
            txt_upper = item.text.upper().strip()
            if any(word in txt_upper for word in self.IGNORED_NAME_WORDS):
                continue
            clean = re.sub(r'[^A-Z\s.]', '', txt_upper).strip()
            words = clean.split()
            if 1 <= len(words) <= 4 and len(clean) >= 3:
                candidates.append((item, clean.title()))

        if candidates:
            return candidates[0]

        return None, None

    def _extract_address(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str], Optional[BoundingBox]]:
        """Extracts multi-line address block using Address / Perm Add anchors."""
        address_items = []
        anchor_found = False

        for item in ocr_result.items:
            txt = item.text.strip()
            if self.ADDRESS_ANCHOR_RE.search(txt) or anchor_found:
                anchor_found = True
                if "GOVERNMENT" not in txt.upper() and "DRIVING" not in txt.upper():
                    clean = re.sub(r'^(?:ADDRESS|ADD|PERM ADD|S/O|W/O|D/O)[:\s]*', '', txt, flags=re.IGNORECASE).strip()
                    if clean:
                        address_items.append(item)
                if self.PINCODE_RE.search(txt):
                    break

        if address_items:
            full_addr = ", ".join([it.text.strip() for it in address_items])
            primary_item = address_items[0]

            xs = [it.bounding_box.x for it in address_items if it.bounding_box]
            ys = [it.bounding_box.y for it in address_items if it.bounding_box]
            x2s = [it.bounding_box.x + it.bounding_box.width for it in address_items if it.bounding_box]
            y2s = [it.bounding_box.y + it.bounding_box.height for it in address_items if it.bounding_box]

            merged_bbox = BoundingBox(x=min(xs), y=min(ys), width=max(x2s) - min(xs), height=max(y2s) - min(ys)) if xs else primary_item.bounding_box
            return primary_item, full_addr, merged_bbox

        return None, None, None

    def _extract_vehicle_classes(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str]]:
        """Extracts Vehicle Classes / COV (e.g. MCWG, LMV, TRANS)."""
        found_classes = set()
        primary_item = None

        for item in ocr_result.items:
            txt_upper = item.text.upper()
            if self.COV_ANCHOR_RE.search(txt_upper) or any(vc in txt_upper for vc in KNOWN_VEHICLE_CLASSES):
                if not primary_item:
                    primary_item = item
                for vc in KNOWN_VEHICLE_CLASSES:
                    if re.search(r'\b' + re.escape(vc) + r'\b', txt_upper):
                        found_classes.add(vc)

        if found_classes:
            return primary_item, ", ".join(sorted(found_classes))
        return None, None

    def _extract_issuing_authority(self, ocr_result: OCRResult) -> Tuple[Optional[OCRItem], Optional[str]]:
        """Extracts RTO or Licensing Authority."""
        for item in ocr_result.items:
            txt = item.text.strip()
            if self.RTO_ANCHOR_RE.search(txt):
                clean = re.sub(r'^(?:ISSUING AUTHORITY|LICENSING AUTHORITY|RTO|R\.T\.O|ISSUED BY)[:\s]*', '', txt, flags=re.IGNORECASE).strip()
                if clean:
                    return item, clean.title()

        # Look for RTO state pattern e.g. RTO PUNE / RTO MUMBAI / LICENSING AUTHORITY DELHI
        for item in ocr_result.items:
            txt_upper = item.text.upper()
            if "RTO" in txt_upper or "LICENSING AUTHORITY" in txt_upper or "TRANSPORT DEPT" in txt_upper:
                return item, item.text.strip().title()

        return None, None

    def _build_validation_summary(self,
                                  dl_number: Optional[ExtractedField],
                                  name: Optional[ExtractedField],
                                  dob: Optional[ExtractedField],
                                  issue_date: Optional[ExtractedField],
                                  expiry_date: Optional[ExtractedField],
                                  is_dl_format_valid: bool,
                                  is_chronology_valid: bool) -> Dict[str, Any]:
        """Builds validation summary metadata for Driving Licence."""
        present_fields = []
        missing_fields = []

        for k, v in [("driving_licence_number", dl_number), ("name", name), ("date_of_birth", dob), ("date_of_issue", issue_date), ("validity_expiry_date", expiry_date)]:
            if v and v.value:
                present_fields.append(k)
            else:
                missing_fields.append(k)

        summary_text = (
            f"Extracted {len(present_fields)}/5 core fields. "
            f"State RTO DL Format: {'VALID' if is_dl_format_valid else 'UNVERIFIED/NON_STANDARD'}. "
            f"Date Chronology (Issue < Expiry): {'VALID' if is_chronology_valid else 'INVALID_CHRONOLOGY'}. "
            f"Disclaimer: Internal formatting checks DO NOT constitute official Parivahan database verification."
        )

        return {
            "required_fields_present": present_fields,
            "missing_required_fields": missing_fields,
            "is_dl_format_valid": is_dl_format_valid,
            "is_chronology_valid": is_chronology_valid,
            "summary_text": summary_text
        }
