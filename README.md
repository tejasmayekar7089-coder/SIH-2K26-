# SIH26188 — AI-Based Fake Identity & Document Screening System

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green.svg)](https://fastapi.tiangolo.com/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-red.svg)](https://docs.pydantic.dev/)

> **Subtitle:** *Evidence Driven • Explainable • Modular • Pretrained First • Officer Decides*  
> **Smart India Hackathon 2026 Submission**

---

## 🎯 Architecture Overview

The **SIH26188 Screening System** is an enterprise-grade document and identity screening platform designed to assist border verification officers. It extracts multi-modal signals, computes ICAO 9303 checksums, isolates pixel-level tampering via DocTamper/TruFor, performs strict 1:1 facial biometric matching, aggregates evidence into an immutable schema, and presents transparent, explainable reason codes to the human decision-maker.

```
USER ➔ 1. INPUT ➔ 2. QUALITY ➔ 3. DOC INTEL ➔ [4A. MRZ / 4B. METADATA]
     ➔ 5. DETERMINISTIC VALIDATION ➔ 6. TAMPERING AI (CORE INNOVATION)
     ➔ 7. FIELD MAPPING ➔ 8. CONDITIONAL 1:1 FACE ➔ 9. MOCK INTEL DB
     ➔ 10. EVIDENCE BUILDER ➔ 11. FRAUD HYPOTHESIS ➔ 12. RISK ENGINE
     ➔ 13. OFFICER DASHBOARD ➔ 14. AUDIT TRAIL
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10 or higher
- Node.js 18+ (for Frontend)
- SQLite3

### 2. Backend Setup
```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run initial setup and seed mock DB
python ../scripts/setup.py

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```
API Documentation will be live at: [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Dashboard will be live at: [http://localhost:5173](http://localhost:5173)

---

## 👥 Workstream Ownership Guide for Team of 3

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ DEVELOPER 1: DOCUMENT INTELLIGENCE & VALIDATION                                        │
│ • Module 2: Acquisition & OpenCV Quality (backend/app/modules/acquisition/)            │
│ • Module 3: PaddleOCR & Portrait Crop (backend/app/modules/document_intelligence/)     │
│ • Module 4A: ICAO 9303 MRZ Parsing (backend/app/modules/mrz/)                          │
│ • Module 4B: Metadata Extraction (backend/app/modules/metadata/)                       │
│ • Module 5: Deterministic Validation Engine (backend/app/modules/validation/)          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ DEVELOPER 2: TAMPERING & CORE AI INNOVATION                                            │
│ • Module 6: DocTamper / DTD Model Pipeline (backend/app/modules/tampering/)            │
│ • Module 6: TruFor Fallback Architecture (backend/app/modules/tampering/)              │
│ • Module 6: Heatmap & Localization Masks (backend/app/modules/tampering/)              │
│ • Module 7: Field-Evidence Spatial IoU Mapping (backend/app/modules/field_mapping/)    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ DEVELOPER 3: FACE VERIFICATION & UI INTEGRATION                                        │
│ • Module 8: InsightFace / ArcFace 1:1 Biometrics (backend/app/modules/face/)           │
│ • Module 9: Mock External Intelligence DB (backend/app/modules/external_intelligence/) │
│ • Module 1: Ingestion API Endpoints (backend/app/api/routes/upload.py)                 │
│ • Module 13: Officer Dashboard Frontend (frontend/src/)                                │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ INTEGRATION LEAD: ARCHITECTURE & REASONING                                             │
│ • Common Evidence Schema (backend/app/schemas/evidence.py)                             │
│ • Module 10: Evidence Builder Normalizer (backend/app/modules/evidence/)               │
│ • Module 11: Fraud Hypothesis Engine (backend/app/modules/hypothesis/)                 │
│ • Module 12: Rule-Based Risk Engine (backend/app/modules/risk/)                        │
│ • Module 14: Immutable Audit Trail (backend/app/modules/audit/)                         │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧪 Running Automated Tests
```bash
cd backend
pytest tests/ -v
```

---

## ⚖️ License
Distributed under the MIT License. See [`LICENSE`](LICENSE) for more information.
