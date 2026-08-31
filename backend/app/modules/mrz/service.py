from typing import List, Optional
from app.schemas.mrz import MRZResult, MRZFormat, CheckDigitVerification, ConsistencyStatus
from app.schemas.extraction import ExtractionResult
from app.modules.document_intelligence.ocr.schemas import OCRResult
from app.modules.mrz.detector import MRZDetector
from app.modules.mrz.parser import TD3MRZParser
from app.modules.mrz.validator import ICAO9303Validator
from app.modules.mrz.consistency import MRZConsistencyChecker
from app.core.logging import get_logger

logger = get_logger("mrz")

class MRZService:
    """Module 4A: MRZ Detection, TD3 Parsing, ICAO 9303 Checksum Verification & Printed VIZ Consistency."""

    def __init__(self):
        self.detector = MRZDetector()
        self.parser = TD3MRZParser()
        self.validator = ICAO9303Validator()
        self.consistency_checker = MRZConsistencyChecker()

    def compute_icao_check_digit(self, input_str: str) -> str:
        """Expose explicit ICAO 9303 check digit calculation."""
        return self.validator.compute_check_digit(input_str)

    def process_passport_mrz(self, ocr_result: Optional[OCRResult], extraction: Optional[ExtractionResult]) -> MRZResult:
        """Alias for parse_and_validate."""
        return self.parse_and_validate(extraction=extraction, ocr_result=ocr_result)

    def parse_and_validate(self, extraction: ExtractionResult, ocr_result: Optional[OCRResult] = None) -> MRZResult:
        """Executes Detector -> Parser -> Validator -> Consistency Checker pipeline."""
        logger.info("Executing MRZ processing pipeline...")

        # 1. MRZ Detection
        raw_lines = []
        bbox = None
        if ocr_result:
            raw_lines, bbox = self.detector.detect_mrz(ocr_result)

        # Fallback check if raw_text contains MRZ lines
        if not raw_lines and extraction and extraction.raw_text:
            lines = [ln.strip().replace(" ", "") for ln in extraction.raw_text.splitlines() if len(ln.strip().replace(" ", "")) >= 30]
            if len(lines) >= 2:
                raw_lines = [lines[-2][:44], lines[-1][:44]]

        if not raw_lines or len(raw_lines) < 2:
            logger.info("No valid 2-line MRZ detected in document.")
            return MRZResult(
                is_present=False,
                mrz_format=MRZFormat.NONE,
                parsing_errors=["No MRZ lines detected in document text or layout."]
            )

        # 2. MRZ Parsing
        parsed_data = self.parser.parse(raw_lines)
        if parsed_data.mrz_format == MRZFormat.NONE:
            return MRZResult(
                is_present=False,
                mrz_format=MRZFormat.NONE,
                raw_mrz_lines=raw_lines,
                parsing_errors=["Failed to parse TD3 MRZ structure."]
            )

        # 3. ICAO 9303 Check Digit Validation
        verifications, all_check_digits_valid = self.validator.validate_mrz_data(parsed_data)

        # 4. Printed VIZ vs. MRZ Field Consistency Verification
        consistency_checks, overall_consistency = self.consistency_checker.verify_consistency(extraction, parsed_data)

        # Format dates to YYYY-MM-DD
        dob_norm = self.consistency_checker._format_mrz_date(parsed_data.date_of_birth, is_expiry=False)
        exp_norm = self.consistency_checker._format_mrz_date(parsed_data.expiry_date, is_expiry=True)

        raw_mrz_text = "\n".join(raw_lines)

        return MRZResult(
            is_present=True,
            mrz_format=MRZFormat.TD3,
            raw_mrz_lines=raw_lines,
            raw_mrz_text=raw_mrz_text,
            bounding_box=bbox,
            document_type=parsed_data.document_code,
            country_code=parsed_data.issuing_state,
            surname=parsed_data.surname,
            given_names=parsed_data.given_names,
            document_number=parsed_data.passport_number,
            nationality=parsed_data.nationality,
            date_of_birth=dob_norm,
            gender=parsed_data.sex,
            expiry_date=exp_norm,
            optional_data=parsed_data.optional_data,
            check_digits=verifications,
            all_check_digits_valid=all_check_digits_valid,
            consistency_checks=consistency_checks,
            overall_consistency_status=overall_consistency,
            parsing_errors=[]
        )
