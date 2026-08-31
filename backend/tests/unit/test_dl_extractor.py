import pytest
import numpy as np
from app.schemas.common import BoundingBox
from app.schemas.document import DocumentCategory
from app.modules.document_intelligence.ocr.schemas import OCRItem, OCRResult
from app.modules.document_intelligence.extractors.driving_licence import DrivingLicenceFieldExtractor

def test_smart_card_dl_extraction_mh_format():
    extractor = DrivingLicenceFieldExtractor()
    bbox_head = BoundingBox(x=100, y=20, width=400, height=30)
    bbox_dl = BoundingBox(x=100, y=60, width=300, height=30)
    bbox_name = BoundingBox(x=100, y=100, width=250, height=25)
    bbox_dob = BoundingBox(x=100, y=130, width=200, height=25)
    bbox_doi = BoundingBox(x=100, y=160, width=200, height=25)
    bbox_doe = BoundingBox(x=100, y=190, width=200, height=25)
    bbox_cov = BoundingBox(x=100, y=220, width=200, height=25)
    bbox_rto = BoundingBox(x=100, y=250, width=300, height=25)

    items = [
        OCRItem(text="MAHARASHTRA STATE MOTOR VEHICLES DEPT", confidence=0.99, bounding_box=bbox_head),
        OCRItem(text="DRIVING LICENCE", confidence=0.98, bounding_box=bbox_head),
        OCRItem(text="DL NO: MH-12-20180012345", confidence=0.97, bounding_box=bbox_dl),
        OCRItem(text="NAME: PRIYA SHARMA", confidence=0.96, bounding_box=bbox_name),
        OCRItem(text="DOB: 20/10/1995", confidence=0.95, bounding_box=bbox_dob),
        OCRItem(text="ISSUE DATE: 15/01/2018", confidence=0.94, bounding_box=bbox_doi),
        OCRItem(text="VALID TILL: 14/01/2038", confidence=0.94, bounding_box=bbox_doe),
        OCRItem(text="COV: MCWG, LMV", confidence=0.95, bounding_box=bbox_cov),
        OCRItem(text="ISSUING AUTHORITY: RTO PUNE", confidence=0.93, bounding_box=bbox_rto)
    ]
    ocr_result = OCRResult(items=items, engine_name="paddleocr")
    ocr_result.rebuild_full_text()

    result = extractor.extract_fields(ocr_result)

    assert result.document_category == DocumentCategory.DRIVING_LICENSE
    assert result.document_number is not None
    assert result.document_number.field_name == "driving_licence_number"
    assert result.document_number.value == "MH-12-20180012345"
    assert result.document_number.severity == "LOW"
    assert result.document_number.provenance == "ocr:state_rto_format_matched"

    assert result.full_name is not None
    assert result.full_name.value == "Priya Sharma"

    assert result.date_of_birth is not None
    assert result.date_of_birth.value == "1995-10-20"

    assert result.issue_date is not None
    assert result.issue_date.value == "2018-01-15"

    assert result.expiry_date is not None
    assert result.expiry_date.value == "2038-01-14"
    assert result.expiry_date.severity == "LOW"

    assert "vehicle_classes" in result.additional_fields
    assert "LMV" in result.additional_fields["vehicle_classes"].value
    assert "MCWG" in result.additional_fields["vehicle_classes"].value

    assert "issuing_authority" in result.additional_fields
    assert "Rto Pune" in result.additional_fields["issuing_authority"].value

def test_date_chronology_anomaly_detection():
    extractor = DrivingLicenceFieldExtractor()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)

    # Inverted dates: Issue Date (2035) > Expiry Date (2020)
    items = [
        OCRItem(text="DL NO: DL-0420110012345", confidence=0.98, bounding_box=bbox),
        OCRItem(text="ISSUE DATE: 15/01/2035", confidence=0.94, bounding_box=bbox),
        OCRItem(text="VALID TILL: 14/01/2020", confidence=0.94, bounding_box=bbox)
    ]
    ocr_result = OCRResult(items=items, engine_name="paddleocr")
    ocr_result.rebuild_full_text()

    result = extractor.extract_fields(ocr_result)

    assert result.expiry_date is not None
    assert result.expiry_date.severity == "HIGH"
    assert result.expiry_date.provenance == "ocr:chronology_anomaly_invalid_dates"

    val_summary = result.additional_fields["validation_summary"].value
    assert "INVALID_CHRONOLOGY" in val_summary

def test_unidentifiable_fields_graceful_null():
    extractor = DrivingLicenceFieldExtractor()
    bbox = BoundingBox(x=0, y=0, width=10, height=10)

    # Partial OCR with missing DOB and Address
    items = [
        OCRItem(text="DRIVING LICENCE", confidence=0.98, bounding_box=bbox),
        OCRItem(text="DL NO: KA01-20200001234", confidence=0.97, bounding_box=bbox)
    ]
    ocr_result = OCRResult(items=items, engine_name="paddleocr")
    ocr_result.rebuild_full_text()

    result = extractor.extract_fields(ocr_result)

    assert result.document_number is not None
    assert result.document_number.value == "KA01-20200001234"
    assert result.date_of_birth is None
    assert result.address is None
    assert "vehicle_classes" not in result.additional_fields
