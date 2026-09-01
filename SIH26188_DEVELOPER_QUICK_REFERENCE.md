# SIH26188 — Developer Quick Reference Guide

> **Target Audience**: New developers, teammates, and reviewers joining the SIH26188 project.  
> **Goal**: Get running, understand the architecture, and locate key code within 15 minutes.

---

## 🚀 1. How to Run the Project locally

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 18+ (for React Frontend)

### Step 1: Start the Backend (FastAPI)
```powershell
cd C:\Document-Intelligence\SIH26188\backend
..\.venv\Scripts\activate
$env:PYTHONPATH="."
python -m uvicorn app.main:app --reload --port 8000
```
- **API Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### Step 2: Start the Frontend (React + Vite)
```powershell
cd C:\Document-Intelligence\SIH26188\frontend
npm run dev
```
- **Dashboard UI**: [http://localhost:5173](http://localhost:5173)

### Step 3: Run the Automated Unit Test Suite
```powershell
cd C:\Document-Intelligence\SIH26188
$env:PYTHONPATH="backend"
.venv\Scripts\python.exe -m pytest backend/tests
```

---

## 🏗️ 2. Core Architecture Summary

```
DOCUMENT UPLOAD
      ↓
M2: ACQUISITION & QUALITY (OpenCV Blur / Glare)
      ↓
M3: DOCUMENT INTELLIGENCE (PaddleOCR + Classifier + Field Extractors)
      ↓
M4A: MRZ TD3 PARSER (ICAO 7-3-1 Checkdigits) ── M4B: EXIF METADATA
      ↓                                                ↓
M5: DETERMINISTIC VALIDATION (Aadhaar, Passport, DL Rules Engine)
      ↓
M6: TAMPERING AI (ELA Residuals + SRM High-Pass Noise Filter + 2D Heatmaps)
      ↓
M7: FIELD-TAMPER SPATIAL IoU MAPPER
      ↓
M8: 1:1 FACE VERIFICATION CROP ── M9: EXTERNAL INTEL DB
      ↓                                    ↓
M10: EVIDENCE BUILDER NORMALIZER
      ↓
M11: FRAUD HYPOTHESIS ENGINE
      ↓
M12: DYNAMIC RISK SCORING ENGINE (LOW / MEDIUM / HIGH)
      ↓
M13: OFFICER DASHBOARD UI (React + Visual Heatmaps)
      ↓
M14: IMMUTABLE AUDIT LOGGING (SQLite Database)
```

---

## 📂 3. Most Important Files Map

| Module / Topic | Core Implementation File | Important Functions / Classes |
| :--- | :--- | :--- |
| **API Routers** | [`backend/app/api/routes/documents.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/api/routes/documents.py) | `analyze_document()` |
| **Quality (M2)** | [`backend/app/modules/acquisition/quality.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/acquisition/quality.py) | `QualityAnalyzer.compute_metrics()` |
| **OCR & Classification (M3)** | [`backend/app/modules/document_intelligence/pipeline.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/document_intelligence/pipeline.py) | `DocumentIntelligencePipeline.process_document()` |
| **MRZ Checksums (M4A)** | [`backend/app/modules/mrz/parser.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/mrz/parser.py) | `TD3Parser.parse()`, `compute_check_digit()` |
| **Validation Rules (M5)** | [`backend/app/modules/validation/service.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/validation/service.py) | `ValidationService.perform_deterministic_validation()` |
| **Tampering AI (M6)** | [`backend/app/modules/tampering/service.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/tampering/service.py) | `TamperingAIService.analyze_tampering()` |
| **Spatial IoU Mapping (M7)** | [`backend/app/modules/field_mapping/service.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/field_mapping/service.py) | `FieldMappingService.map_tamper_to_fields()` |
| **Evidence Synthesis (M10)** | [`backend/app/modules/evidence/builder.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/evidence/builder.py) | `EvidenceBuilderService.build_evidence_bundle()` |
| **Risk Engine (M12)** | [`backend/app/modules/risk/engine.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/modules/risk/engine.py) | `RiskEngine.compute_risk()` |
| **Frontend UI (M13)** | [`frontend/src/App.jsx`](file:///C:/Document-Intelligence/SIH26188/frontend/src/App.jsx) | `handleSubmit()`, Result Panels & Heatmap View |

---

## 🛠️ 4. Debugging Guide

### 1. OCR Returns Empty Text
- Check image blur score in M2 output (`quality_score`).
- Inspect raw PaddleOCR logs or run standalone test: `pytest backend/tests/unit/test_ocr.py`.

### 2. Heatmap Image Not Showing on Frontend
- Verify `/outputs` static mount in [`main.py`](file:///C:/Document-Intelligence/SIH26188/backend/app/main.py).
- Check `data/outputs/` directory to ensure JPEG heatmaps are being generated.

---

## 📋 5. System Health Status

- **Backend Unit Tests**: **85 Passed, 0 Failed**
- **Frontend Build**: Verified with `vite build`
- **Main Audit Report**: See [`SIH26188_COMPLETE_TECHNICAL_AUDIT.md`](file:///C:/Document-Intelligence/SIH26188/SIH26188_COMPLETE_TECHNICAL_AUDIT.md)
