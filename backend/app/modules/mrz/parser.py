import re
from typing import Dict, Any, Optional, List, Tuple
from app.schemas.mrz import MRZFormat
from app.core.logging import get_logger

logger = get_logger("mrz_parser")

def _normalize_mrz_digits(s: str) -> str:
    """Normalizes common OCR misreads in numeric slots (dates, check digits)."""
    trans = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "i": "1", "S": "5", "s": "5", "B": "8", "Z": "2", "G": "6"})
    return s.translate(trans)

class ParsedMRZData:
    def __init__(self,
                 mrz_format: MRZFormat = MRZFormat.TD3,
                 document_code: str = "",
                 issuing_state: str = "",
                 surname: str = "",
                 given_names: str = "",
                 passport_number: str = "",
                 passport_number_check_digit: str = "",
                 nationality: str = "",
                 date_of_birth: str = "",
                 dob_check_digit: str = "",
                 sex: str = "",
                 expiry_date: str = "",
                 expiry_check_digit: str = "",
                 optional_data: str = "",
                 optional_check_digit: str = "",
                 composite_check_digit: str = "",
                 raw_lines: List[str] = None):
        self.mrz_format = mrz_format
        self.document_code = document_code
        self.issuing_state = issuing_state
        self.surname = surname
        self.given_names = given_names
        self.passport_number = passport_number
        self.passport_number_check_digit = passport_number_check_digit
        self.nationality = nationality
        self.date_of_birth = date_of_birth
        self.dob_check_digit = dob_check_digit
        self.sex = sex
        self.expiry_date = expiry_date
        self.expiry_check_digit = expiry_check_digit
        self.optional_data = optional_data
        self.optional_check_digit = optional_check_digit
        self.composite_check_digit = composite_check_digit
        self.raw_lines = raw_lines or []

class TD3MRZParser:
    """Parses ICAO 9303 TD3 standard (2 lines x 44 chars) passport MRZ."""

    @staticmethod
    def parse(raw_lines: List[str]) -> ParsedMRZData:
        """Parse raw 2-line MRZ string list into ParsedMRZData with safe OCR normalization."""
        if not raw_lines or len(raw_lines) < 2:
            logger.warning("TD3MRZParser received fewer than 2 MRZ lines.")
            return ParsedMRZData(mrz_format=MRZFormat.NONE)

        line1 = raw_lines[0].ljust(44, '<')[:44]
        line2 = raw_lines[1].ljust(44, '<')[:44]

        # Line 1 Breakdown (44 chars):
        # 0..2: Document Code (P<)
        # 2..5: Issuing State (e.g. IND)
        # 5..44: Name Field (Surname<<Given<Names)
        doc_code = line1[0:2].replace("<", "")
        issuing_state = line1[2:5].replace("<", "")
        name_field = line1[5:44]

        surname, given_names = TD3MRZParser._parse_mrz_name(name_field)

        # Line 2 Breakdown (44 chars):
        # 0..9: Passport Number (9 chars)
        # 9..10: Passport Number Check Digit (1 char)
        # 10..13: Nationality (3 chars)
        # 13..19: Date of Birth (YYMMDD - 6 chars)
        # 19..20: DOB Check Digit (1 char)
        # 20..21: Sex (M/F/< - 1 char)
        # 21..27: Expiry Date (YYMMDD - 6 chars)
        # 27..28: Expiry Check Digit (1 char)
        # 28..42: Optional / Personal Number (14 chars)
        # 42..43: Optional Check Digit (1 char)
        # 43..44: Composite Check Digit (1 char)
        passport_num_raw = line2[0:9]
        passport_num = passport_num_raw.replace("<", "").upper()
        
        # Check digit, DOB, Expiry normalization
        pass_cd = _normalize_mrz_digits(line2[9:10])
        nationality = line2[10:13].replace("<", "").upper()
        
        dob = _normalize_mrz_digits(line2[13:19])
        dob_cd = _normalize_mrz_digits(line2[19:20])
        
        sex = line2[20:21].upper()
        if sex not in ["M", "F", "X"]:
            sex = "M" if "M" in sex else ("F" if "F" in sex else "<")
        sex = sex.replace("<", "U")

        expiry = _normalize_mrz_digits(line2[21:27])
        expiry_cd = _normalize_mrz_digits(line2[27:28])
        
        optional_raw = line2[28:42]
        optional_data = optional_raw.replace("<", "")
        optional_cd = _normalize_mrz_digits(line2[42:43])
        composite_cd = _normalize_mrz_digits(line2[43:44])

        logger.info(f"[MRZ] TD3MRZParser parsed MRZ for doc {passport_num} ({surname}, {given_names})")

        return ParsedMRZData(
            mrz_format=MRZFormat.TD3,
            document_code=doc_code,
            issuing_state=issuing_state,
            surname=surname,
            given_names=given_names,
            passport_number=passport_num,
            passport_number_check_digit=pass_cd,
            nationality=nationality,
            date_of_birth=dob,
            dob_check_digit=dob_cd,
            sex=sex,
            expiry_date=expiry,
            expiry_check_digit=expiry_cd,
            optional_data=optional_data,
            optional_check_digit=optional_cd,
            composite_check_digit=composite_cd,
            raw_lines=[line1, line2]
        )

    @staticmethod
    def _parse_mrz_name(name_field: str) -> Tuple[str, str]:
        """Parses MRZ name field (Surname<<Given<Names) into (surname, given_names)."""
        parts = name_field.split("<<", 1)
        surname = parts[0].replace("<", " ").strip() if len(parts) > 0 else ""
        given_names = parts[1].replace("<", " ").strip() if len(parts) > 1 else ""
        return surname, given_names
