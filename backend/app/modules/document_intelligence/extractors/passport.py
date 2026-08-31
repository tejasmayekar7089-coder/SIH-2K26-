import re
from typing import Optional, Dict
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.document import DocumentCategory
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.modules.document_intelligence.extractors.base import BaseFieldExtractor
from app.core.logging import get_logger

logger = get_logger("passport_extractor")

class PassportFieldExtractor(BaseFieldExtractor):
    """Field extractor for ICAO Standard Passports."""

    PASSPORT_NUM_RE = re.compile(r'\b([A-PR-WYa-pr-wy]\d{7})\b')
    GENERIC_PASS_RE = re.compile(r'(?:PASSPORT\s*NO|NO)[:\s]*([A-Z0-9]{8,9})', re.IGNORECASE)
    DOB_RE = re.compile(r'(?:DOB|DATE OF BIRTH)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    EXPIRY_RE = re.compile(r'(?:EXPIRY|DATE OF EXPIRY)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    ISSUE_RE = re.compile(r'(?:ISSUE|DATE OF ISSUE)[:\s]*(\d{2}[/\-.]\d{2}[/\-.]\d{4})', re.IGNORECASE)
    MRZ_LINE1_RE = re.compile(r'P[A-Z0-9<]{43}')
    MRZ_LINE2_RE = re.compile(r'[A-Z0-9<]{44}')

    def extract_fields(self, ocr_result: OCRResult) -> ExtractionResult:
        full_name: Optional[ExtractedField] = None
        date_of_birth: Optional[ExtractedField] = None
        document_number: Optional[ExtractedField] = None
        nationality: Optional[ExtractedField] = ExtractedField(
            field_name="Nationality",
            value="IND",
            confidence=0.95
        )
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

        # 1. Extract MRZ lines if present for additional fields
        mrz_lines = []
        for item in ocr_result.items:
            m1 = self.MRZ_LINE1_RE.search(item.text.replace(" ", ""))
            if m1:
                mrz_lines.append(m1.group(0))
            else:
                m2 = self.MRZ_LINE2_RE.search(item.text.replace(" ", ""))
                if m2:
                    mrz_lines.append(m2.group(0))

        if len(mrz_lines) >= 2:
            additional["mrz_line1"] = ExtractedField(field_name="MRZ Line 1", value=mrz_lines[0], confidence=0.98)
            additional["mrz_line2"] = ExtractedField(field_name="MRZ Line 2", value=mrz_lines[1], confidence=0.98)

        # 2. Extract Passport Number from printed VIZ text first
        for item in ocr_result.items:
            # Skip MRZ lines when looking for printed VIZ document number
            if self.MRZ_LINE1_RE.search(item.text.replace(" ", "")) or self.MRZ_LINE2_RE.search(item.text.replace(" ", "")):
                continue
            m = self.PASSPORT_NUM_RE.search(item.text) or self.GENERIC_PASS_RE.search(item.text)
            if m:
                document_number = ExtractedField(
                    field_name="Document Number",
                    value=m.group(1).upper(),
                    confidence=item.confidence,
                    bounding_box=item.bounding_box
                )
                break

        # Fallback to MRZ Line 2 document number if no VIZ doc number found
        if not document_number and len(mrz_lines) >= 2:
            doc_num_mrz = mrz_lines[1][:9].replace("<", "")
            if doc_num_mrz:
                document_number = ExtractedField(
                    field_name="Document Number",
                    value=doc_num_mrz,
                    confidence=0.98
                )

        # 3. Extract DOB
        for item in ocr_result.items:
            m = self.DOB_RE.search(item.text)
            if m:
                date_of_birth = ExtractedField(
                    field_name="Date of Birth",
                    value=m.group(1).strip(),
                    confidence=item.confidence,
                    bounding_box=item.bounding_box
                )
                break

        # 4. Extract Expiry & Issue Dates
        for item in ocr_result.items:
            m = self.EXPIRY_RE.search(item.text)
            if m:
                expiry_date = ExtractedField(
                    field_name="Expiry Date",
                    value=m.group(1).strip(),
                    confidence=item.confidence,
                    bounding_box=item.bounding_box
                )
            m_iss = self.ISSUE_RE.search(item.text)
            if m_iss:
                issue_date = ExtractedField(
                    field_name="Issue Date",
                    value=m_iss.group(1).strip(),
                    confidence=item.confidence,
                    bounding_box=item.bounding_box
                )

        # 5. Extract Name (Surname / Given Name lines)
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
                confidence=0.92
            )

        # 6. Extract Gender
        for item in ocr_result.items:
            txt_upper = item.text.upper().strip()
            if txt_upper in ["SEX M", "SEX F", "SEX / SEX M", "SEX / SEX F"] or "GENDER M" in txt_upper or "GENDER F" in txt_upper:
                g_val = "M" if "M" in txt_upper else "F"
                gender = ExtractedField(
                    field_name="Gender",
                    value=g_val,
                    confidence=item.confidence,
                    bounding_box=item.bounding_box
                )
                break

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
