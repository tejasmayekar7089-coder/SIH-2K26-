import os
import tempfile
import pytest
import numpy as np
from PIL import Image, ImageDraw

from app.schemas.document import ValidatedInputDocument, FileFormat
from app.schemas.metadata import MetadataResult, MetadataClassification
from app.modules.metadata.analyzer import IsolatedMetadataAnalyzer
from app.modules.metadata.service import MetadataService

def create_temp_image_with_exif(filename: str, software: str = None, make: str = None) -> str:
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, filename)
    img = Image.new("RGB", (400, 300), color=(200, 220, 240))
    exif = img.getexif()

    # 0x013B = Artist, 0x0131 = Software, 0x010F = Make, 0x0110 = Model
    if software:
        exif[0x0131] = software
    if make:
        exif[0x010F] = make
        exif[0x0110] = "Test Camera Model v1"

    img.save(path, exif=exif)
    return path

def test_metadata_analysis_supporting_camera_exif():
    path = create_temp_image_with_exif("test_cam_exif.jpg", make="Canon")
    try:
        analyzer = IsolatedMetadataAnalyzer()
        res = analyzer.analyze_file(path, document_id="DOC-CAM-001")

        assert res.has_exif is True
        assert res.device_make == "Canon"
        assert res.device_model == "Test Camera Model v1"
        assert res.image_width == 400
        assert res.image_height == 300
        assert res.aspect_ratio == 1.333
        assert res.metadata_classification == MetadataClassification.SUPPORTING
        assert res.has_editing_signature is False
        assert "Supporting evidence only" in res.supporting_notes
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_metadata_analysis_suspicious_editing_software():
    path = create_temp_image_with_exif("test_photoshop_exif.jpg", software="Adobe Photoshop CC 2024")
    try:
        analyzer = IsolatedMetadataAnalyzer()
        res = analyzer.analyze_file(path, document_id="DOC-EDIT-001")

        assert res.has_exif is True
        assert res.software_signature == "Adobe Photoshop CC 2024"
        assert res.metadata_classification == MetadataClassification.SUSPICIOUS_METADATA
        assert res.has_editing_signature is True
        assert "Software editing signature" in res.supporting_notes
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_metadata_analysis_no_exif():
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "test_no_exif.png")
    img = Image.new("RGB", (500, 300), color=(100, 100, 100))
    img.save(path)  # Standard PNG without EXIF

    try:
        analyzer = IsolatedMetadataAnalyzer()
        res = analyzer.analyze_file(path, document_id="DOC-NOEXIF-001")

        assert res.has_exif is False
        assert res.metadata_classification == MetadataClassification.NOT_AVAILABLE
        assert res.has_editing_signature is False
        assert "EXIF metadata missing, stripped, or unavailable" in res.supporting_notes
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_metadata_analysis_non_existent_file():
    analyzer = IsolatedMetadataAnalyzer()
    res = analyzer.analyze_file("non_existent_file_9999.jpg", document_id="DOC-ERR-001")

    assert res.file_size_bytes == 0
    assert res.has_exif is False
    assert res.metadata_classification == MetadataClassification.NOT_AVAILABLE
    assert "File not found" in res.supporting_notes

def test_metadata_analysis_malformed_corrupt_file():
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "test_corrupt_meta.jpg")
    with open(path, "wb") as f:
        f.write(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x00\x00\x01CORRUPTED_PAYLOAD")

    try:
        analyzer = IsolatedMetadataAnalyzer()
        res = analyzer.analyze_file(path, document_id="DOC-CORRUPT-001")

        assert res.metadata_classification == MetadataClassification.NOT_AVAILABLE
    finally:
        if os.path.exists(path):
            os.remove(path)

def test_metadata_service_integration():
    path = create_temp_image_with_exif("test_service_cam.jpg", make="Samsung")
    try:
        service = MetadataService()
        doc = ValidatedInputDocument(
            document_id="DOC-SRV-001",
            file_name="test_service_cam.jpg",
            file_format=FileFormat.JPG,
            mime_type="image/jpeg",
            file_size_bytes=os.path.getsize(path),
            sha256_checksum="dummy",
            storage_path=path
        )
        res = service.extract_metadata(doc)

        assert res.device_make == "Samsung"
        assert res.metadata_classification == MetadataClassification.SUPPORTING
    finally:
        if os.path.exists(path):
            os.remove(path)
