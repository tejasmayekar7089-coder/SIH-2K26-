# Developer 1 — OCR & Document Intelligence Testing Guide

This guide explains how to test Module 2 (Acquisition & Quality) and Module 3 (Document Intelligence Foundation) in the SIH26188 backend.

---

## 1. Safety & Legal Compliance Notice

> [!IMPORTANT]
> - **NO REAL GOVERNMENT DATABASE CONNECTIVITY**: This system operates entirely offline and locally. It does NOT connect to Aadhaar (UIDAI), PAN (ITD), Parivahan (DL), or Passport Seva databases.
> - **SYNTHETIC TEST DATA ONLY**: All testing and verification MUST be performed using synthetic, mock, or sample documents. Never upload real unconsented citizen identity records.

---

## 2. Environment Setup

Ensure Python 3.10+ is installed and dependencies are met:

```bash
cd backend
py -m pip install -r requirements.txt
```

---

## 3. Running Unit Tests

Run the full automated test suite covering document loading, OpenCV quality metrics, OCR result normalization, classification, and field extraction:

```bash
# Run all unit tests
py -m pytest

# Run specific module tests with detailed verbosity
py -m pytest tests/unit/test_loader.py -v
py -m pytest tests/unit/test_quality.py -v
py -m pytest tests/unit/test_ocr.py -v
py -m pytest tests/unit/test_classifier.py -v
py -m pytest tests/unit/test_doc_intel.py -v
```

---

## 4. Running a Simple Python OCR Test Script

You can run a quick standalone Python script to test image loading, OpenCV quality evaluation, PaddleOCR engine extraction, and document classification on any sample image file (`.jpg`, `.png`, `.webp`, `.tiff`, or `.pdf`):

```python
import os
from app.schemas.document import ValidatedInputDocument, FileFormat
from app.modules.acquisition.service import AcquisitionService
from app.modules.document_intelligence.service import DocumentIntelligenceService

# 1. Path to your synthetic document image or PDF
test_file_path = "path/to/synthetic_sample.jpg"

doc_input = ValidatedInputDocument(
    document_id="DOC-TEST-SAMPLE",
    file_name=os.path.basename(test_file_path),
    file_format=FileFormat.JPG,
    mime_type="image/jpeg",
    file_size_bytes=os.path.getsize(test_file_path),
    sha256_checksum="dummy_checksum",
    storage_path=test_file_path
)

# 2. Execute Module 2 (Acquisition & OpenCV Quality Analysis)
acq_service = AcquisitionService()
quality_result = acq_service.evaluate_and_preprocess(doc_input)
print("=== Quality Analysis Result ===")
print(f"Overall Quality Score: {quality_result.quality_score}")
print(f"Blur Variance: {quality_result.blur_score} (Blurred: {quality_result.is_blurred})")
print(f"Glare Ratio: {quality_result.glare_score} (Glare: {quality_result.has_glare})")
print(f"Processed Image Saved To: {quality_result.processed_image_path}")

# 3. Execute Module 3 (PaddleOCR Engine + Heuristic Classifier + Field Extraction)
doc_intel_service = DocumentIntelligenceService()
extraction = doc_intel_service.extract_document_features(
    doc_input,
    image_path=quality_result.processed_image_path
)

print("\n=== Document Intelligence Result ===")
print(f"Classified Category: {extraction.document_category.value} (Confidence: {extraction.category_confidence})")
print(f"Document Number: {extraction.document_number.value if extraction.document_number else 'N/A'}")
print(f"Full Name: {extraction.full_name.value if extraction.full_name else 'N/A'}")
print(f"Date of Birth: {extraction.date_of_birth.value if extraction.date_of_birth else 'N/A'}")
print(f"Has Portrait Photo: {extraction.has_portrait}")
print(f"Raw OCR Text:\n{extraction.raw_text}")
```

---

## 5. Testing via FastAPI Endpoints

Start up the backend server:

```bash
py -m uvicorn app.main:app --reload --port 8000
```

### Option A: Upload & Document Intelligence Endpoint
Send a `POST` request to `http://localhost:8000/api/v1/upload` followed by `http://localhost:8000/api/v1/document-intelligence/process`.

### Option B: Full Pipeline Screening Endpoint
Send a `POST` request to `http://localhost:8000/api/v1/screening/process` with the `ValidatedInputDocument` payload to observe complete end-to-end execution.
