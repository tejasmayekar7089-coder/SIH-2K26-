import re
from datetime import datetime
from typing import List, Optional, Tuple
from app.schemas.extraction import ExtractionResult
from app.schemas.mrz import MRZResult, FieldConsistencyCheck, ConsistencyStatus
from app.modules.mrz.parser import ParsedMRZData
from app.core.logging import get_logger

logger = get_logger("mrz_consistency")

class MRZConsistencyChecker:
    """Compares printed VIZ (Visual Inspection Zone) OCR fields against parsed MRZ fields."""

    @classmethod
    def verify_consistency(cls, extraction: ExtractionResult, parsed_mrz: ParsedMRZData) -> Tuple[List[FieldConsistencyCheck], ConsistencyStatus]:
        """
        Cross-checks printed OCR extraction result against parsed MRZ data.
        Returns (list_of_checks, overall_consistency_status).
        """
        if not parsed_mrz or not parsed_mrz.raw_lines:
            return [], ConsistencyStatus.NOT_AVAILABLE

        checks: List[FieldConsistencyCheck] = []

        # 1. Passport Number Comparison
        viz_pass_num = extraction.document_number.value if extraction.document_number else None
        mrz_pass_num = parsed_mrz.passport_number if parsed_mrz.passport_number else None
        checks.append(cls._compare_strings(
            "Passport Number",
            viz_pass_num,
            mrz_pass_num,
            confidence=extraction.document_number.confidence if extraction.document_number else 0.0
        ))

        # 2. Date of Birth Comparison
        viz_dob = extraction.date_of_birth.value if extraction.date_of_birth else None
        mrz_dob_norm = cls._format_mrz_date(parsed_mrz.date_of_birth, is_expiry=False)
        checks.append(cls._compare_dates(
            "Date of Birth",
            viz_dob,
            mrz_dob_norm,
            confidence=extraction.date_of_birth.confidence if extraction.date_of_birth else 0.0
        ))

        # 3. Expiry Date Comparison
        viz_exp = extraction.expiry_date.value if extraction.expiry_date else None
        mrz_exp_norm = cls._format_mrz_date(parsed_mrz.expiry_date, is_expiry=True)
        checks.append(cls._compare_dates(
            "Expiry Date",
            viz_exp,
            mrz_exp_norm,
            confidence=extraction.expiry_date.confidence if extraction.expiry_date else 0.0
        ))

        # 4. Nationality Comparison
        viz_nat = extraction.nationality.value if extraction.nationality else None
        mrz_nat = parsed_mrz.nationality if parsed_mrz.nationality else None
        checks.append(cls._compare_strings(
            "Nationality",
            viz_nat,
            mrz_nat,
            confidence=extraction.nationality.confidence if extraction.nationality else 0.0
        ))

        # 5. Full Name Comparison
        viz_name = extraction.full_name.value if extraction.full_name else None
        mrz_name = f"{parsed_mrz.surname} {parsed_mrz.given_names}".strip()
        checks.append(cls._compare_names(
            "Full Name",
            viz_name,
            mrz_name,
            confidence=extraction.full_name.confidence if extraction.full_name else 0.0
        ))

        # Overall Status Determination
        statuses = [c.status for c in checks]
        if ConsistencyStatus.MISMATCH in statuses:
            overall = ConsistencyStatus.MISMATCH
        elif all(s == ConsistencyStatus.MATCH for s in statuses if s != ConsistencyStatus.NOT_AVAILABLE):
            overall = ConsistencyStatus.MATCH
        elif ConsistencyStatus.LOW_CONFIDENCE in statuses:
            overall = ConsistencyStatus.LOW_CONFIDENCE
        else:
            overall = ConsistencyStatus.NOT_AVAILABLE

        logger.info(f"MRZConsistencyChecker completed: Overall Status = {overall.value}")
        return checks, overall

    @staticmethod
    def _compare_strings(field_name: str, viz_val: Optional[str], mrz_val: Optional[str], confidence: float) -> FieldConsistencyCheck:
        if not viz_val or not mrz_val:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.NOT_AVAILABLE,
                notes="One or both fields missing for comparison."
            )

        v_clean = re.sub(r'\s+', '', viz_val.upper())
        m_clean = re.sub(r'\s+', '', mrz_val.upper())

        if confidence < 0.60:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.LOW_CONFIDENCE,
                notes="Printed OCR confidence below 0.60 threshold."
            )

        if v_clean == m_clean:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.MATCH,
                notes="Exact match between printed VIZ and MRZ."
            )

        return FieldConsistencyCheck(
            field_name=field_name,
            printed_viz_value=viz_val,
            mrz_value=mrz_val,
            status=ConsistencyStatus.MISMATCH,
            notes=f"Mismatch: VIZ '{viz_val}' != MRZ '{mrz_val}'"
        )

    @staticmethod
    def _compare_dates(field_name: str, viz_val: Optional[str], mrz_val: Optional[str], confidence: float) -> FieldConsistencyCheck:
        if not viz_val or not mrz_val:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.NOT_AVAILABLE,
                notes="Date field unavailable."
            )

        v_digits = re.sub(r'\D', '', viz_val)
        m_digits = re.sub(r'\D', '', mrz_val)

        # Check if year/month/day components match
        if v_digits.endswith(m_digits) or m_digits in v_digits:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.MATCH,
                notes="Date components match."
            )

        return FieldConsistencyCheck(
            field_name=field_name,
            printed_viz_value=viz_val,
            mrz_value=mrz_val,
            status=ConsistencyStatus.MISMATCH,
            notes=f"Date mismatch: VIZ '{viz_val}' != MRZ '{mrz_val}'"
        )

    @staticmethod
    def _compare_names(field_name: str, viz_val: Optional[str], mrz_val: Optional[str], confidence: float) -> FieldConsistencyCheck:
        if not viz_val or not mrz_val:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.NOT_AVAILABLE,
                notes="Name field unavailable."
            )

        v_words = set(re.sub(r'[^A-Z\s]', '', viz_val.upper()).split())
        m_words = set(re.sub(r'[^A-Z\s]', '', mrz_val.upper()).split())

        overlap = v_words.intersection(m_words)
        if len(overlap) >= 1:
            return FieldConsistencyCheck(
                field_name=field_name,
                printed_viz_value=viz_val,
                mrz_value=mrz_val,
                status=ConsistencyStatus.MATCH,
                notes=f"Name words match: {overlap}"
            )

        return FieldConsistencyCheck(
            field_name=field_name,
            printed_viz_value=viz_val,
            mrz_value=mrz_val,
            status=ConsistencyStatus.MISMATCH,
            notes="Name mismatch between VIZ and MRZ."
        )

    @staticmethod
    def _format_mrz_date(yymmdd: Optional[str], is_expiry: bool = False) -> Optional[str]:
        """Converts MRZ YYMMDD string into YYYY-MM-DD format."""
        if not yymmdd or len(yymmdd) != 6 or not yymmdd.isdigit():
            return yymmdd
        yy = int(yymmdd[0:2])
        mm = yymmdd[2:4]
        dd = yymmdd[4:6]
        if is_expiry:
            yyyy = 2000 + yy if yy <= 80 else 1900 + yy
        else:
            curr_yy = datetime.now().year % 100
            yyyy = 2000 + yy if yy <= curr_yy else 1900 + yy
        return f"{yyyy}-{mm}-{dd}"
