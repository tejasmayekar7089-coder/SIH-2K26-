from typing import List, Tuple
from app.schemas.mrz import CheckDigitVerification
from app.modules.mrz.parser import ParsedMRZData
from app.core.logging import get_logger

logger = get_logger("icao9303_validator")

class ICAO9303Validator:
    """Explicit ICAO 9303 check-digit calculation and validation engine."""

    WEIGHTS = [7, 3, 1]

    @classmethod
    def compute_check_digit(cls, input_str: str) -> str:
        """
        Computes ICAO 9303 check digit.
        Character values: 0-9 => 0-9, A-Z => 10-35, < => 0
        Weights: 7, 3, 1 repeating
        Formula: sum(val * weight) mod 10
        """
        total = 0
        for i, char in enumerate(input_str):
            weight = cls.WEIGHTS[i % 3]
            c_upper = char.upper()
            if c_upper.isdigit():
                val = int(c_upper)
            elif c_upper.isalpha():
                val = ord(c_upper) - 55  # 'A' (65) -> 10, 'B' (66) -> 11, ... 'Z' (90) -> 35
            elif c_upper == '<':
                val = 0
            else:
                val = 0
            total += val * weight
        return str(total % 10)

    @classmethod
    def validate_mrz_data(cls, parsed_data: ParsedMRZData) -> Tuple[List[CheckDigitVerification], bool]:
        """
        Validates all ICAO 9303 check digits for a parsed TD3 MRZ structure.
        Returns (list_of_verifications, all_check_digits_valid).
        """
        if not parsed_data or not parsed_data.raw_lines or len(parsed_data.raw_lines) < 2:
            return [], False

        verifications: List[CheckDigitVerification] = []
        line2 = parsed_data.raw_lines[1].ljust(44, '<')[:44]

        # 1. Passport Number Check Digit (Line 2, chars 0..9 vs char 9)
        pass_num_raw = line2[0:9]
        expected_pass_cd = line2[9:10]
        computed_pass_cd = cls.compute_check_digit(pass_num_raw)
        verifications.append(CheckDigitVerification(
            field_name="Passport Number Check Digit",
            extracted_value=pass_num_raw.replace("<", ""),
            expected_check_digit=expected_pass_cd,
            computed_check_digit=computed_pass_cd,
            is_valid=(expected_pass_cd == computed_pass_cd)
        ))

        # 2. Date of Birth Check Digit (Line 2, chars 13..19 vs char 19)
        dob_raw = line2[13:19]
        expected_dob_cd = line2[19:20]
        computed_dob_cd = cls.compute_check_digit(dob_raw)
        verifications.append(CheckDigitVerification(
            field_name="Date of Birth Check Digit",
            extracted_value=dob_raw,
            expected_check_digit=expected_dob_cd,
            computed_check_digit=computed_dob_cd,
            is_valid=(expected_dob_cd == computed_dob_cd)
        ))

        # 3. Expiry Date Check Digit (Line 2, chars 21..27 vs char 27)
        expiry_raw = line2[21:27]
        expected_exp_cd = line2[27:28]
        computed_exp_cd = cls.compute_check_digit(expiry_raw)
        verifications.append(CheckDigitVerification(
            field_name="Expiry Date Check Digit",
            extracted_value=expiry_raw,
            expected_check_digit=expected_exp_cd,
            computed_check_digit=computed_exp_cd,
            is_valid=(expected_exp_cd == computed_exp_cd)
        ))

        # 4. Optional Data Check Digit (Line 2, chars 28..42 vs char 42)
        optional_raw = line2[28:42]
        expected_opt_cd = line2[42:43]
        computed_opt_cd = cls.compute_check_digit(optional_raw)
        is_opt_valid = (expected_opt_cd == computed_opt_cd) if expected_opt_cd != "<" else True
        verifications.append(CheckDigitVerification(
            field_name="Optional Data Check Digit",
            extracted_value=optional_raw.replace("<", ""),
            expected_check_digit=expected_opt_cd,
            computed_check_digit=computed_opt_cd,
            is_valid=is_opt_valid
        ))

        # 5. Composite Check Digit (Line 2, chars 0..10 + 13..20 + 21..43 vs char 43)
        composite_payload = line2[0:10] + line2[13:20] + line2[21:43]
        expected_comp_cd = line2[43:44]
        computed_comp_cd = cls.compute_check_digit(composite_payload)
        verifications.append(CheckDigitVerification(
            field_name="Composite Check Digit",
            extracted_value="composite_payload",
            expected_check_digit=expected_comp_cd,
            computed_check_digit=computed_comp_cd,
            is_valid=(expected_comp_cd == computed_comp_cd)
        ))

        all_valid = all(v.is_valid for v in verifications)
        logger.info(f"ICAO9303Validator finished: {len(verifications)} check digits evaluated, All Valid: {all_valid}")

        return verifications, all_valid
