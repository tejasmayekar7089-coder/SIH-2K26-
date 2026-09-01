import re
from typing import Optional, Dict
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.document import DocumentCategory
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.modules.document_intelligence.extractors.base import BaseFieldExtractor
from app.core.logging import get_logger

logger = get_logger("passport_extractor")

class PassportFieldExtractor(BaseFieldExtractor):
    """Field extractor for ICAO Standard Passports with VIZ and MRZ synchronization."""

    PASSPORT_NUM_RE = re.compile(r'\b([A-PR-WYa-pr-wy]\d{7})\b')
    GENERIC_PASS_RE = re.compile(r'(?:PASSPORT\s*(?:NO|NUMBER)|NO)[:\s]*([A-Z0-9]{8,9})', re.IGNORECASE)
    DOB_RE = re.compile(r'(?:DOB|DATE OF BIRTH|BIRTH)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    EXPIRY_RE = re.compile(r'(?:EXPIRY|DATE OF EXPIRY|EXP)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    ISSUE_RE = re.compile(r'(?:ISSUE|DATE OF ISSUE)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    GENERIC_DATE_RE = re.compile(r'\b(\d{2}[/\-.]\d{2}[/\-.]\d{4})\b')
    MRZ_LINE1_RE = re.compile(r'P[A-Z0-9<]{30,44}')
    MRZ_LINE2_RE = re.compile(r'[A-Z0-9<]{30,44}')

    def extract_fields(self, ocr_result: OCRResult) -> ExtractionResult:
        full_name: Optional[ExtractedField] = None
        date_of_birth: Optional[ExtractedField] = None
        document_number: Optional[ExtractedField] = None
        nationality: Optional[ExtractedField] = None
        gender: Optional[ExtractedField] = None
        expiry_date: Optional[ExtractedField] = None
        issue_date: Optional[ExtractedField] = None
        additional: Dict[str, ExtractedField] = {}

        if not ocr_result or not ocr_result.items:
            return ExtractionResult(
                document_category=DocumentCategory.PASSPORT,
                category_confidence=0.95,
                raw_text=ocr_result.full_text if ocr_result else "",
                ocr_confidence_mean=ocr_result.mean_confidence if ocr_result else 0.0
            )

        # 1. Detect MRZ candidate lines from OCR items
        mrz_lines = []
        for item in ocr_result.items:
            cleaned = item.text.upper().replace(" ", "").replace("«", "<")
            if cleaned.startswith("P<") and len(cleaned) >= 25:
                mrz_lines.append(cleaned[:44].ljust(44, '<'))
            elif len(cleaned) >= 30 and "<" in cleaned and not cleaned.startswith("P<") and sum(c.isdigit() for c in cleaned) >= 5:
                mrz_lines.append(cleaned[:44].ljust(44, '<'))

        if len(mrz_lines) >= 2:
            additional["mrz_line1"] = ExtractedField(field_name="MRZ Line 1", value=mrz_lines[0], confidence=0.98, provenance="ocr:mrz")
            additional["mrz_line2"] = ExtractedField(field_name="MRZ Line 2", value=mrz_lines[1], confidence=0.98, provenance="ocr:mrz")

        # 2. Extract Passport Number from VIZ text
        for item in ocr_result.items:
            if "<" in item.text:
                continue
            m = self.PASSPORT_NUM_RE.search(item.text) or self.GENERIC_PASS_RE.search(item.text)
            if m:
                document_number = ExtractedField(
                    field_name="Document Number",
                    value=m.group(1).upper(),
                    confidence=item.confidence,
                    bounding_box=item.bounding_box,
                    provenance="ocr:viz"
                )
                break

        # Fallback to MRZ Line 2 document number if no VIZ doc number found
        if not document_number and len(mrz_lines) >= 2:
            doc_num_mrz = mrz_lines[1][:9].replace("<", "")
            if doc_num_mrz:
                document_number = ExtractedField(
                    field_name="Document Number",
                    value=doc_num_mrz,
                    confidence=0.95,
                    provenance="ocr:mrz_sync"
                )

        # 3. Extract DOB, Expiry, and Issue Dates
        found_dates = []
        for item in ocr_result.items:
            if "<" in item.text:
                continue
            m_dob = self.DOB_RE.search(item.text)
            if m_dob and not date_of_birth:
                date_of_birth = ExtractedField(field_name="Date of Birth", value=m_dob.group(1).strip(), confidence=item.confidence, bounding_box=item.bounding_box, provenance="ocr:viz")

            m_exp = self.EXPIRY_RE.search(item.text)
            if m_exp and not expiry_date:
                expiry_date = ExtractedField(field_name="Expiry Date", value=m_exp.group(1).strip(), confidence=item.confidence, bounding_box=item.bounding_box, provenance="ocr:viz")

            m_iss = self.ISSUE_RE.search(item.text)
            if m_iss and not issue_date:
                issue_date = ExtractedField(field_name="Issue Date", value=m_iss.group(1).strip(), confidence=item.confidence, bounding_box=item.bounding_box, provenance="ocr:viz")

            for dm in self.GENERIC_DATE_RE.findall(item.text):
                found_dates.append((dm, item.confidence, item.bounding_box))

        # Date fallback logic if explicit labels weren't present
        if len(found_dates) >= 3:
            if not date_of_birth:
                date_of_birth = ExtractedField(field_name="Date of Birth", value=found_dates[0][0], confidence=found_dates[0][1], bounding_box=found_dates[0][2], provenance="ocr:heuristic")
            if not issue_date:
                issue_date = ExtractedField(field_name="Issue Date", value=found_dates[1][0], confidence=found_dates[1][1], bounding_box=found_dates[1][2], provenance="ocr:heuristic")
            if not expiry_date:
                expiry_date = ExtractedField(field_name="Expiry Date", value=found_dates[2][0], confidence=found_dates[2][1], bounding_box=found_dates[2][2], provenance="ocr:heuristic")

        # 4. Extract Name (Surname / Given Name lines)
        surnames = []
        given_names = []
        for idx, item in enumerate(ocr_result.items):
            txt_upper = item.text.upper()
            if "SURNAME" in txt_upper:
                val = re.sub(r'^(?:SURNAME)[:\s]*', '', txt_upper).strip()
                if val:
                    surnames.append(val)
                elif idx + 1 < len(ocr_result.items):
                    surnames.append(ocr_result.items[idx + 1].text.upper().strip())
            elif "GIVEN NAME" in txt_upper or "GIVEN NAMES" in txt_upper:
                val = re.sub(r'^(?:GIVEN NAME|GIVEN NAMES)[:\s]*', '', txt_upper).strip()
                if val:
                    given_names.append(val)
                elif idx + 1 < len(ocr_result.items):
                    given_names.append(ocr_result.items[idx + 1].text.upper().strip())

        if surnames or given_names:
            combined_name = f"{' '.join(surnames)}, {' '.join(given_names)}".strip(", ")
            full_name = ExtractedField(
                field_name="Full Name",
                value=combined_name,
                confidence=0.92,
                provenance="ocr:viz"
            )

        # Fallback to MRZ Line 1 Name if no VIZ name found
        if not full_name and len(mrz_lines) >= 1:
            name_field = mrz_lines[0][5:44]
            parts = name_field.split("<<", 1)
            sur = parts[0].replace("<", " ").strip() if len(parts) > 0 else ""
            giv = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
            if sur or giv:
                mrz_name = f"{sur}, {giv}".strip(", ")
                full_name = ExtractedField(field_name="Full Name", value=mrz_name, confidence=0.95, provenance="ocr:mrz_sync")

        # 5. Extract Gender
        for item in ocr_result.items:
            txt_upper = item.text.upper().strip()
            if txt_upper in ["SEX M", "SEX F", "SEX / SEX M", "SEX / SEX F"] or "GENDER M" in txt_upper or "GENDER F" in txt_upper:
                g_val = "M" if "M" in txt_upper else "F"
                gender = ExtractedField(
                    field_name="Gender",
                    value=g_val,
                    confidence=item.confidence,
                    bounding_box=item.bounding_box,
                    provenance="ocr:viz"
                )
                break

        if not gender and len(mrz_lines) >= 2:
            sex_mrz = mrz_lines[1][20:21].upper()
            if sex_mrz in ["M", "F"]:
                gender = ExtractedField(field_name="Gender", value=sex_mrz, confidence=0.95, provenance="ocr:mrz_sync")

        # 6. Extract Nationality
        for item in ocr_result.items:
            txt_upper = item.text.upper().strip()
            if "NATIONALITY" in txt_upper or "REPUBLIC OF INDIA" in txt_upper or "INDIAN" in txt_upper:
                val = "IND" if ("INDIAN" in txt_upper or "INDIA" in txt_upper or "IND" in txt_upper) else txt_upper
                nationality = ExtractedField(field_name="Nationality", value="IND", confidence=0.95, provenance="ocr:viz")
                break

        if not nationality and len(mrz_lines) >= 2:
            nat_mrz = mrz_lines[1][10:13].replace("<", "").upper()
            if nat_mrz:
                nationality = ExtractedField(field_name="Nationality", value=nat_mrz, confidence=0.95, provenance="ocr:mrz_sync")
        elif not nationality:
            nationality = ExtractedField(field_name="Nationality", value="IND", confidence=0.90, provenance="ocr:default")

        return ExtractionResult(
            document_category=DocumentCategory.PASSPORT,
            category_confidence=0.98,
            full_name=full_name,
            date_of_birth=date_of_birth,
            document_number=document_number,
            nationality=nationality,
            gender=gender,
            expiry_date=expiry_date,
            issue_date=issue_date,
            additional_fields=additional,
            raw_text=ocr_result.full_text,
            ocr_confidence_mean=ocr_result.mean_confidence
        )

