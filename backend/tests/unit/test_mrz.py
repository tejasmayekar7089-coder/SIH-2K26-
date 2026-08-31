import pytest
from app.schemas.document import DocumentCategory
from app.schemas.extraction import ExtractionResult, ExtractedField
from app.schemas.mrz import MRZFormat, ConsistencyStatus
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.mrz.service import MRZService
from app.modules.mrz.validator import ICAO9303Validator
from app.modules.mrz.parser import TD3MRZParser, ParsedMRZData

def test_icao_9303_check_digit_algorithm():
    validator = ICAO9303Validator()

    # Known ICAO 9303 test cases:
    # Character values: 0-9 => 0-9, A-Z => 10-35, < => 0. Weights: 7, 3, 1 repeating
    cd_pass = validator.compute_check_digit("P8923412<")
    assert cd_pass == "8"

    # Date of birth "920514" -> (9*7 + 2*3 + 0*1 + 5*7 + 1*3 + 4*1) % 10 = 1
    cd_dob = validator.compute_check_digit("920514")
    assert cd_dob == "1"

    # Expiry date "320513" -> (3*7 + 2*3 + 0*1 + 5*7 + 1*3 + 3*1) % 10 = 8
    cd_exp = validator.compute_check_digit("320513")
    assert cd_exp == "8"

def test_valid_td3_mrz_parsing_and_verification():
    mrz_service = MRZService()

    line1 = "P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = "P8923412<8IND9205141M3205138<<<<<<<<<<<0<<<6"

    items = [
        OCRItem(text=line1, confidence=0.99),
        OCRItem(text=line2, confidence=0.99)
    ]
    ocr_res = OCRResult(items=items)

    extraction = ExtractionResult(
        document_category=DocumentCategory.PASSPORT,
        document_number=ExtractedField(field_name="document_number", value="P8923412", confidence=0.98),
        date_of_birth=ExtractedField(field_name="date_of_birth", value="1992-05-14", confidence=0.95),
        expiry_date=ExtractedField(field_name="expiry_date", value="2032-05-13", confidence=0.95),
        nationality=ExtractedField(field_name="nationality", value="IND", confidence=0.98),
        full_name=ExtractedField(field_name="name", value="Arjun Sharma", confidence=0.96)
    )

    res = mrz_service.parse_and_validate(extraction, ocr_res)

    assert res.is_present is True
    assert res.mrz_format == MRZFormat.TD3
    assert res.document_number == "P8923412"
    assert res.surname == "SHARMA"
    assert res.given_names == "ARJUN"
    assert res.nationality == "IND"
    assert res.date_of_birth == "1992-05-14"
    assert res.gender == "M"
    assert res.expiry_date == "2032-05-13"

    assert len(res.check_digits) == 5
    assert res.all_check_digits_valid is True
    assert res.overall_consistency_status == ConsistencyStatus.MATCH

def test_invalid_mrz_check_digit_detection():
    mrz_service = MRZService()

    # Corrupted check digit for Passport Number (expected 9, computed 8)
    line1 = "P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = "P8923412<9IND9205141M3205138<<<<<<<<<<<0<<<6"

    items = [
        OCRItem(text=line1, confidence=0.99),
        OCRItem(text=line2, confidence=0.99)
    ]
    ocr_res = OCRResult(items=items)

    extraction = ExtractionResult(document_category=DocumentCategory.PASSPORT)

    res = mrz_service.parse_and_validate(extraction, ocr_res)

    assert res.is_present is True
    assert res.all_check_digits_valid is False
    pass_cd_check = next(c for c in res.check_digits if c.field_name == "Passport Number Check Digit")
    assert pass_cd_check.is_valid is False
    assert pass_cd_check.expected_check_digit == "9"
    assert pass_cd_check.computed_check_digit == "8"

def test_ocr_mrz_field_mismatch_detection():
    mrz_service = MRZService()

    # MRZ has Passport Number P8923412, printed VIZ OCR has X9999999
    line1 = "P<INDSHARMA<<ARJUN<<<<<<<<<<<<<<<<<<<<<<<<<<"
    line2 = "P8923412<8IND9205141M3205138<<<<<<<<<<<0<<<6"

    ocr_res = OCRResult(items=[OCRItem(text=line1, confidence=0.99), OCRItem(text=line2, confidence=0.99)])

    extraction = ExtractionResult(
        document_category=DocumentCategory.PASSPORT,
        document_number=ExtractedField(field_name="document_number", value="X9999999", confidence=0.95)
    )

    res = mrz_service.parse_and_validate(extraction, ocr_res)

    assert res.overall_consistency_status == ConsistencyStatus.MISMATCH
    num_check = next(c for c in res.consistency_checks if c.field_name == "Passport Number")
    assert num_check.status == ConsistencyStatus.MISMATCH
    assert num_check.printed_viz_value == "X9999999"
    assert num_check.mrz_value == "P8923412"

def test_missing_mrz_handling():
    mrz_service = MRZService()

    ocr_res = OCRResult(items=[OCRItem(text="SAMPLE PASSPORT VIZ TEXT ONLY", confidence=0.90)])
    extraction = ExtractionResult(document_category=DocumentCategory.PASSPORT)

    res = mrz_service.parse_and_validate(extraction, ocr_res)

    assert res.is_present is False
    assert res.mrz_format == MRZFormat.NONE
    assert len(res.parsing_errors) >= 1
