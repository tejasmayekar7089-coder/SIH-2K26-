import pytest
import numpy as np
from app.schemas.common import BoundingBox
from app.schemas.document import DocumentCategory
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.extractors.aadhaar import (
    AadhaarFieldExtractor,
    verhoeff_validate,
    mask_aadhaar_number
)

def test_verhoeff_checksum_algorithm():
    # Valid synthetic 12-digit Aadhaar numbers with valid Verhoeff check digits
    assert verhoeff_validate("234567890122") is True
    assert verhoeff_validate("987654321097") is True

    # Invalid check digits
    assert verhoeff_validate("234567890120") is False
    assert verhoeff_validate("111111111112") is False
    assert verhoeff_validate("1234") is False  # Less than 12 digits

def test_privacy_aadhaar_masking():
    # Never log full Aadhaar number
    masked1 = mask_aadhaar_number("234567890122")
    assert masked1 == "XXXX-XXXX-0122"
    assert "23456789" not in masked1

    masked2 = mask_aadhaar_number("9876 5432 1097")
    assert masked2 == "XXXX-XXXX-1097"
    assert "9876" not in masked2

def test_front_side_aadhaar_extraction():
    extractor = AadhaarFieldExtractor()
    bbox_head = BoundingBox(x=100, y=20, width=400, height=40)
    bbox_name = BoundingBox(x=100, y=80, width=250, height=30)
    bbox_dob = BoundingBox(x=100, y=120, width=200, height=25)
    bbox_gen = BoundingBox(x=100, y=150, width=100, height=25)
    bbox_num = BoundingBox(x=150, y=220, width=300, height=35)

    items = [
        OCRItem(text="GOVERNMENT OF INDIA", confidence=0.99, bounding_box=bbox_head),
        OCRItem(text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA", confidence=0.98, bounding_box=bbox_head),
        OCRItem(text="ARJUN SHARMA", confidence=0.96, bounding_box=bbox_name),
        OCRItem(text="DOB: 14/05/1992", confidence=0.95, bounding_box=bbox_dob),
        OCRItem(text="MALE", confidence=0.99, bounding_box=bbox_gen),
        OCRItem(text="2345 6789 0122", confidence=0.98, bounding_box=bbox_num)
    ]
    ocr_result = OCRResult(items=items, engine_name="paddleocr")
    ocr_result.rebuild_full_text()

    result = extractor.extract_fields(ocr_result)

    assert result.document_category == DocumentCategory.AADHAAR
    assert result.document_number is not None
    assert result.document_number.field_name == "aadhaar_number"
    assert result.document_number.value == "2345 6789 0122"
    assert result.document_number.confidence == 0.98
    assert result.document_number.source == "paddleocr"
    assert result.document_number.provenance == "ocr:verhoeff_checksum_matched"
    assert result.document_number.bbox == [150, 220, 450, 255]

    assert result.full_name is not None
    assert result.full_name.value == "Arjun Sharma"
    assert result.full_name.provenance == "ocr:spatial_heading_heuristic"

    assert result.date_of_birth is not None
    assert result.date_of_birth.value == "1992-05-14"
    assert result.date_of_birth.provenance == "ocr:dob_label_matched"

    assert result.gender is not None
    assert result.gender.value == "MALE"

def test_back_side_aadhaar_address_extraction():
    extractor = AadhaarFieldExtractor()
    bbox_head = BoundingBox(x=50, y=20, width=400, height=30)
    bbox_addr1 = BoundingBox(x=50, y=70, width=450, height=25)
    bbox_addr2 = BoundingBox(x=50, y=100, width=450, height=25)
    bbox_addr3 = BoundingBox(x=50, y=130, width=450, height=25)
    bbox_num = BoundingBox(x=150, y=200, width=300, height=35)

    items = [
        OCRItem(text="UNIQUE IDENTIFICATION AUTHORITY OF INDIA", confidence=0.98, bounding_box=bbox_head),
        OCRItem(text="Address: S/O RAKESH SHARMA", confidence=0.94, bounding_box=bbox_addr1),
        OCRItem(text="HOUSE NO 123, MG ROAD, SECTOR 15", confidence=0.92, bounding_box=bbox_addr2),
        OCRItem(text="NEW DELHI, 110001", confidence=0.95, bounding_box=bbox_addr3),
        OCRItem(text="2345 6789 0122", confidence=0.98, bounding_box=bbox_num)
    ]
    ocr_result = OCRResult(items=items, engine_name="paddleocr")
    ocr_result.rebuild_full_text()

    result = extractor.extract_fields(ocr_result)

    assert result.address is not None
    assert result.address.field_name == "address"
    assert "S/O RAKESH SHARMA" in result.address.value
    assert "110001" in result.address.value
    assert result.address.provenance == "ocr:address_anchor_spatial_cluster"
    assert result.address.bbox is not None

def test_date_plausibility_validation():
    extractor = AadhaarFieldExtractor()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)

    # Future birth year (implausible)
    items_future = [
        OCRItem(text="DOB: 15/08/2085", confidence=0.90, bounding_box=bbox)
    ]
    ocr_res_future = OCRResult(items=items_future)
    ocr_res_future.rebuild_full_text()

    res_future = extractor.extract_fields(ocr_res_future)
    val_summary = res_future.additional_fields["validation_summary"].value
    assert "DOB Plausible: NO" in val_summary

    # Valid historic birth year (plausible)
    items_valid = [
        OCRItem(text="DOB: 15/08/1985", confidence=0.90, bounding_box=bbox)
    ]
    ocr_res_valid = OCRResult(items=items_valid)
    ocr_res_valid.rebuild_full_text()

    res_valid = extractor.extract_fields(ocr_res_valid)
    val_summary_valid = res_valid.additional_fields["validation_summary"].value
    assert "DOB Plausible: YES" in val_summary_valid
