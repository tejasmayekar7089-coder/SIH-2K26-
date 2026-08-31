import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app

client = TestClient(app)

def create_valid_test_png_bytes() -> bytes:
    img = Image.new("RGB", (400, 300), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Add sharp grid lines to ensure sharpness
    for i in range(0, 400, 20):
        draw.line([(i, 0), (i, 300)], fill=(0, 0, 0), width=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_api_analyze_document_success():
    png_bytes = create_valid_test_png_bytes()
    files = {
        "document_file": ("test_doc.png", png_bytes, "image/png")
    }

    response = client.post("/api/v1/documents/analyze", files=files)

    assert response.status_code == 200
    data = response.json()
    assert "document_id" in data
    assert "document_type" in data
    assert "quality" in data
    assert "ocr" in data
    assert "extracted_fields" in data
    assert "validation" in data
    assert "evidence" in data
    assert isinstance(data["evidence"], list)

def test_api_analyze_document_unsupported_format():
    files = {
        "document_file": ("test_file.txt", b"Unsupported text content", "text/plain")
    }

    response = client.post("/api/v1/documents/analyze", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "Unsupported file format" in data["detail"]

def test_api_analyze_document_corrupt_payload():
    files = {
        "document_file": ("test_corrupt.png", b"CORRUPTED_NON_IMAGE_BYTES_PAYLOAD", "image/png")
    }

    response = client.post("/api/v1/documents/analyze", files=files)

    assert response.status_code == 400
    data = response.json()
    assert "Corrupted or unreadable image file" in data["detail"]

def test_api_analyze_document_oversized_file(monkeypatch):
    # Mock settings.MAX_UPLOAD_SIZE_MB to 0.0001 (approx 100 bytes) for testing
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0.0001)

    big_payload = b"X" * 200
    files = {
        "document_file": ("big_doc.png", big_payload, "image/png")
    }

    response = client.post("/api/v1/documents/analyze", files=files)

    assert response.status_code == 413
    data = response.json()
    assert "File exceeds maximum allowed size" in data["detail"]
