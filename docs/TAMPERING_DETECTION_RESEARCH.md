# Identity Document Tampering Detection Research

**Project**: SIH26188 Document Intelligence  
**Role**: AI/ML Research Engineer  
**Document Version**: 1.0.0  
**Date**: September 2026  

---

## 1. Objective

The primary objective of this research is to evaluate, compare, and establish practical AI/ML and computer vision approaches for detecting whether an identity document image (such as a Passport, Aadhaar card, Driving Licence, or voter ID) has undergone digital tampering or physical forgery.

Identity document fraud in verification systems typically manifests through several specific manipulation techniques:

1. **Edited Text**: Alteration of printed alphanumeric characters, dates, or numbers using photo-editing tools or vector overlays (e.g., modifying a birth year from `1985` to `1998` or changing a name string).
2. **Changed Fields**: Overwriting or replacing entire text fields (e.g., address, issuing authority, MRZ lines) with non-matching fonts, alignments, or background colors.
3. **Copy-Paste Manipulation (Copy-Move)**: Copying a legitimate region of the document (such as a clear font digit or security emblem) and pasting it over another field to alter information while retaining font consistency.
4. **Image Splicing**: Inserting graphic elements, text snippets, or signatures extracted from a completely different document image into the target document.
5. **Photo Replacement**: Replacing the original holder portrait photograph with a different individual's photo, creating a mismatched identity document.
6. **Cropping & Region Replacement**: Cutting out rectangular document regions and replacing them with synthesized or modified patches.
7. **Inpainting**: Removing text, holograms, or signatures using patch-based or deep generative inpainting techniques (e.g., Telea, Navier-Stokes, or GAN/Diffusion inpainters), leaving smoothed or interpolated background textures.
8. **Digital Overlays & Re-compression Artifacts**: Applying digital watermarks, fake holographic layers, color space adjustments, or multi-stage JPEG re-saving to conceal tampered boundaries.

### Targeted End-to-End Analysis Pipeline

```
Document Image Payload
         │
         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 1: Image Quality Inspection & Preprocessing     │
│  - Dimension scaling, color space check, format check  │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 2: Tampering Analysis Engine                    │
│  - Multi-stream inspection (ELA, Noise, DL Model)      │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 3: Decision & Confidence Scoring                │
│  - Genuine vs. Suspicious classification               │
└────────────────────────┬───────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────┐
│  Stage 4: Evidence & Anomaly Localization              │
│  - Pixel-level Heatmap / Suspicious Bounding Regions   │
│  - Structured Evidence Items for Audit Pipeline       │
└────────────────────────────────────────────────────────┘
```

---

## 2. Requirements

To integrate seamlessly into the SIH26188 Document Intelligence architecture, any proposed tampering detection solution must satisfy the following operational constraints:

* **Classification & Localization Output**: Must provide both a global confidence score ($0.0 \text{ to } 1.0$) indicating overall document authenticity and a 2D spatial heatmap/mask identifying localized tampered regions.
* **Local & Environment Compatibility**: Must run locally on standard server hardware (Windows 11 / Linux, Python 3.12, PyTorch 2.x, OpenCV) or support offloaded inference via Google Colab / dedicated GPU worker.
* **Inference Latency**: Single document analysis must complete within $1.5 \text{ to } 3.5 \text{ seconds}$ on standard CPU or GPU hardware.
* **Sensitivity to Text & Photo Alterations**: Must detect fine-grained text modifications (such as 1-digit date edits) as well as coarse manipulations (such as portrait swapping).
* **Reproducibility & Open Source Weights**: Models must have accessible pretrained weights and executable inference code without requiring proprietary closed APIs.

---

## 3. SIDTD (Synthetic ID and Travel Documents)

### Overview & Dataset Origin
**SIDTD** (Synthetic ID and Travel Documents) is a research dataset developed by Oriol Ramos Terrades et al. (Computer Vision Center, Universitat Autònoma de Barcelona). It addresses the critical shortage of publicly available forged identity documents caused by strict PII (Personally Identifiable Information) regulations. SIDTD builds upon the **MIDV-2020** dataset by using genuine ID card/passport templates as "bona fide" specimens and generating synthetic forgeries using realistic forgery operations.

### Key Characteristics & Technical Specifications
* **Dataset Scope**: Contains thousands of genuine and synthetically forged identity documents covering international passports, identity cards, and driving licences.
* **Manipulation Types Included**:
  * *Crop & Replace*: Replacing text fields or identity photos with content from other specimens.
  * *Synthetic Overlay*: Overwriting alphanumeric fields with artificial fonts.
  * *Face Swapping*: Replacing portrait photos while maintaining document layout.
* **Pretrained Models Benchmarked**:
  * EfficientNet-B3 (CNN baseline)
  * ResNet50 (Standard residual network)
  * Vision Transformer (`ViT-L/16`)
  * TransFG (Fine-Grained Vision Transformer)
  * CoAARC (Co-Attention Attentive Recurrent Network)
* **Official Codebase**: `Oriolrt/SIDTD_Dataset` on GitHub (PyTorch).
* **Task Type**: **Binary Classification** (Genuine vs. Forged). The dataset contains bounding box metadata inherited from MIDV-2020 for region-of-interest extraction, but the primary benchmark models operate as document-level classifiers rather than pixel-level segmentation networks.
* **Hardware & Runtime Requirements**:
  * Python 3.8+ / PyTorch 1.10+ / `timm` / OpenCV / scikit-learn.
  * Inference runs easily on standard CPU (approx. 150-300ms per image) or GPU (< 50ms per image).
  * Compatible with Windows, Linux, and Google Colab.
* **Installation Steps**:
  ```bash
  git clone https://github.com/Oriolrt/SIDTD_Dataset.git
  cd SIDTD_Dataset
  pip install torch torchvision timm opencv-python pandas scikit-learn
  ```

### Limitations & Evaluation for Prototype
* **Strengths**: Specifically designed for identity documents (passports, ID cards); excellent fine-tuning dataset for document classification.
* **Limitations**: Does **not** produce a pixel-level tampering heatmap out of the box; models output global classification scores. Bounding boxes are provided in dataset metadata rather than generated dynamically by model output.

---

## 4. DocTamper

### Overview & Dataset Origin
**DocTamper** is a large-scale dataset and model benchmark presented at CVPR 2023 (*"Towards Robust Tampered Text Detection in Document Image: New Dataset and New Solution"* by Chen et al.). It was created specifically to solve the problem of detecting fine-grained text editing in document images.

### Key Characteristics & Technical Specifications
* **Dataset Scale**: Contains approximately **170,000 document images** (contracts, receipts, financial forms, identity cards, certificates) with pixel-level ground-truth annotations demarcating tampered text regions.
* **Model Architecture (DTD - Document Tampering Detector)**:
  * **Visual Perception Head (VPH)**: Extracts spatial RGB features using a SegFormer / ResNet backbone.
  * **Frequency Perception Head (FPH)**: Converts Discrete Cosine Transform (DCT) coefficients into frequency-domain embeddings to detect subtle compression and noise discrepancies invisible to human eyes.
  * **Multi-view Iterative Decoder (MID)**: Fuses multi-scale spatial and frequency features to produce dense pixel-level tampering probability maps.
* **Official Repository**: `qcf-568/DocTamper` on GitHub.
* **Pretrained Model Availability**:
  * Checkpoints (`dtd_doctamper.pth` / `best.pt`) are available via official drive/repository links.
  * Inference can be executed directly using `batch_infer.py` without retraining.
* **Detection Capability**: Highly specialized in detecting edited, replaced, or inpainted text characters and numbers.
* **Output Format**: Produces a **2D binary pixel-level heatmap / mask** ($H \times W$) highlighting exact tampered text coordinates alongside a global tampering probability score.
* **Dependencies & OS**:
  * Python 3.8+, PyTorch 1.12+, MMCV / MMSegmentation.
  * Runs on Linux, Windows (with PyTorch CPU/CUDA), and Google Colab.
* **Installation Steps**:
  ```bash
  git clone https://github.com/qcf-568/DocTamper.git
  cd DocTamper
  pip install torch torchvision mmcv-full==1.7.0 mmsegmentation==0.30.0 opencv-python
  ```

### Limitations & Evaluation for Prototype
* **Strengths**: State-of-the-art pixel-level text tampering localization; combines frequency and visual features; highly relevant for ID card numbers, names, and dates.
* **Limitations**: MMCV/MMSegmentation dependencies can be tricky to compile on native Windows without C++ build tools (recommended to run via Colab or Docker container). Dataset is dominated by business documents and forms rather than dedicated ID cards.

---

## 5. Alternative Practical Approaches

In addition to heavy deep-learning benchmarks, several classical signal-processing and hybrid vision techniques provide fast, deterministic, and highly effective tampering detection:

### A. Error Level Analysis (ELA)
* **Mechanism**: JPEG compression operates in $8 \times 8$ pixel blocks. When an image is modified and re-saved, tampered regions undergo different levels of JPEG compression error compared to unchanged original regions. ELA re-compresses the image at a known quality level (e.g., 90%) and calculates the absolute error difference:
  $$E(x, y) = |I_{\text{original}}(x,y) - I_{\text{recompressed}}(x,y)|$$
* **Output**: A 2D brightness heatmap where elevated error intensities ("hotspots") pinpoint spliced or edited areas.
* **Suitability**: Excellent for detecting copy-pasted text, inserted signatures, and photo replacements.
* **Execution**: Extremely lightweight ($< 50\text{ms}$ on CPU), 100% open-source, requires zero deep-learning model downloads.

### B. High-Pass Noise Variance & Residual Filter Analysis (SRM)
* **Mechanism**: Digital sensors leave uniform micro-noise patterns across an authentic photograph. Replaced photos or inpainted text disrupt this noise continuity. By passing the image through high-pass Spatial Rich Model (SRM) filters or Laplacian kernels, local noise variance is measured across overlapping image tiles.
* **Output**: A variance discrepancy map highlighting smoothed, inpainted, or spliced regions.
* **Execution**: Pure OpenCV/NumPy arithmetic ($< 30\text{ms}$ on CPU).

### C. TruFor (Transformer-based Image Forgery Detector)
* **Mechanism**: Developed by GRIP-UNINA (CVPR 2023), TruFor combines an RGB Feature Extractor with a learned "Noiseprint++" noise fingerprint extractor feeding a Transformer decoder.
* **Output**: Global forgery probability, 2D localization heatmap, and a confidence map assessing localization reliability.
* **GitHub Repository**: `grip-unina/TruFor`.
* **Execution**: Pretrained PyTorch weights available; runs on GPU and CPU.

### D. CAT-Net (Compression Artifact Tracing Network)
* **Mechanism**: A dual-stream CNN analyzing JPEG DCT coefficients and RGB channels simultaneously to trace double JPEG compression artifacts.
* **GitHub Repository**: `mjkwon2021/CAT-Net`.
* **Suitability**: High for detecting document image splicing and copy-move forgery.

---

## 6. Model Comparison Table

Below is the comprehensive comparison matrix evaluating all candidate approaches across the 20 required parameters:

| Parameter | SIDTD (EfficientNet/ViT) | DocTamper (DTD / SegFormer) | TruFor (RGB + Noiseprint++) | ELA + Light CNN Classifier | SRM High-Pass Noise Filter |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Technique / Model** | Deep CNN / ViT Backbone | Dual-head VPH + FPH + MID | RGB + Noiseprint++ Transformer | Error Level Analysis + ResNet18 | Spatial Rich Model Noise Variance |
| **2. Target Dataset** | SIDTD (MIDV-2020 based) | DocTamper (170k docs) | Diverse Forgery Datasets | CASIA v2.0 / Custom ID Set | Deterministic Signal Analysis |
| **3. Pretrained Model Available?** | Yes (in GitHub repo) | Yes (Drive / Kaggle links) | Yes (Official PyTorch weights) | Yes (Torchvision + ELA Script) | N/A (Algorithm-based) |
| **4. GitHub / Official Repo** | `Oriolrt/SIDTD_Dataset` | `qcf-568/DocTamper` | `grip-unina/TruFor` | Custom / `PhotoHolmes` | Custom / OpenCV Script |
| **5. Can it run locally?** | Yes (Windows CPU/GPU) | Yes (Requires MMCV build) | Yes (Windows / Linux PyTorch) | Yes (100% Native Python) | Yes (100% Native Python) |
| **6. Can it run in Colab?** | Yes | Yes | Yes | Yes | Yes |
| **7. GPU Requirements** | Optional (CPU: ~200ms) | Recommended (GPU: ~80ms) | Recommended (GPU: ~120ms) | Optional (CPU: ~30ms) | Optional (CPU: ~15ms) |
| **8. Python/PyTorch Version** | PyTorch 1.10+, Python 3.8+ | PyTorch 1.12+, Python 3.8+ | PyTorch 1.12+, Python 3.8+ | PyTorch 1.x/2.x, Python 3.8+ | Python 3.x (NumPy, OpenCV) |
| **9. Input Format** | RGB Image Array / File | RGB Image Array / File | RGB Image Array / File | RGB Image / JPEG File | RGB Image Array |
| **10. Output Format** | Class Probabilities | 2D Binary Mask + Score | 2D Heatmap + Score | 2D ELA Image + Score | 2D Noise Variance Map |
| **11. Classification Capability** | **High** (Genuine vs Fake) | **High** (Global Score) | **High** (Global Score) | **Medium** (Classifier Score) | **Low** (Threshold-based) |
| **12. Localization Capability** | **Low** (Classification only)| **High** (Pixel-level Text) | **High** (Region Heatmap) | **Medium** (Visual Heatmap) | **Medium** (Noise Boundary) |
| **13. Heatmap Availability** | No | **Yes** (2D Binary Mask) | **Yes** (2D Anomaly Map) | **Yes** (2D Error Difference) | **Yes** (2D Noise Map) |
| **14. Identity Document Suitability**| **Very High** (Passports/IDs) | **High** (Text/Numbers) | **High** (Photos & Splicing) | **High** (General Documents) | **Medium** (High-res ID Scans) |
| **15. Installation Complexity** | Low (`pip install timm`) | High (MMCV C++ build) | Medium (Standard PyTorch) | **Very Low** (Standard PIL/CV2) | **Very Low** (No dependencies) |
| **16. Technical Problems** | Classification only; no mask | MMCV Windows compilation | Large model size (~250MB) | Sensitive to JPEG quality | High noise on poor scans |
| **17. Limitations** | No localization heatmap | Dataset restricted access | GPU recommended for speed | False positives on sharp edges | Unsuitable for low-res thumbs |
| **18. Additional Training Needed?** | Optional | Optional | No (Inference ready) | Recommended for fine-tuning | No |
| **19. Implementation Difficulty**| Low | Medium-High | Medium | **Very Low** | **Very Low** |
| **20. Prototype Recommendation** | Secondary (Classifier) | Primary (Text Localization)| Primary (Photo Splicing) | **Core Baseline (Fast ELA)** | **Core Baseline (Noise Map)** |

---

## 7. Local/Colab Compatibility Analysis

* **Windows Local Environment (Current System)**:
  * **Native Compatibility**: ELA, High-Pass Noise Variance, and TruFor PyTorch models run directly without custom C++ extensions.
  * **MMCV / DocTamper Note**: Installing `mmcv-full` on native Windows Python 3.12 can encounter MSVC compilation issues. For local execution on Windows, loading the DocTamper PyTorch weights via a simplified SegFormer model wrapper (without heavy MMCV dependencies) is the recommended path.
* **Google Colab Environment**:
  * All models (SIDTD, DocTamper, TruFor, CAT-Net) install and run effortlessly in Google Colab (Linux environment with free T4 GPU support).

---

## 8. Pretrained Model Availability

1. **SIDTD**: Pretrained PyTorch weights for EfficientNet-B3, ResNet50, and ViT are linked in the `Oriolrt/SIDTD_Dataset` GitHub repository releases.
2. **DocTamper**: Official SegFormer / DTD checkpoints (`dtd_doctamper.pth`) are hosted on Google Drive and Kaggle.
3. **TruFor**: Official weights (`trufor.pth`) are hosted on GitHub/Grip-Unina servers and load cleanly via standard PyTorch `torch.load()`.
4. **ELA + ResNet Baseline**: Requires no external downloads; ELA preprocessing converts input images into enhanced residual maps which are fed into a standard Torchvision ResNet18 backbone.

---

## 9. Identity Document Compatibility

Identity documents (Passports, Aadhaar, Driving Licences) present unique features compared to standard natural images:
* **Micro-print & Fine Text**: Dates, passport numbers, and names are rendered in precise fonts. DocTamper and ELA excel at detecting character-level replacements.
* **Portrait Photographs**: Photo replacement on identity documents is best detected using TruFor or High-Pass Noise Variance Analysis, which highlight spatial discrepancies between the background security patterns and the portrait patch.
* **Security Background Grids**: Guilloche patterns and fine background grids reveal splicing artifacts when subjected to ELA and DCT frequency analysis.

---

## 10. Recommended Architecture for SIH26188 Prototype

To achieve maximum accuracy, fast local execution, and explainable evidence generation, we recommend a **Hybrid 4-Stage Tampering Detection Architecture**:

```
                  ┌─────────────────────────────────────┐
                  │    Uploaded Document Image          │
                  └──────────────────┬──────────────────┘
                                     │
         ┌───────────────────────────┼───────────────────────────┐
         ▼                           ▼                           ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│  Stream A: ELA   │       │ Stream B: Noise  │       │ Stream C: TruFor │
│  Residual Engine │       │ Variance (SRM)   │       │ / ResNet DL Head │
└────────┬─────────┘       └────────┬─────────┘       └────────┬─────────┘
         │                           │                           │
         └───────────────────────────┼───────────────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │  Multi-Stream Anomaly Fusion        │
                  │  - Composite Heatmap Generation     │
                  │  - Global Tampering Score (0-1.0)   │
                  └──────────────────┬──────────────────┘
                                     │
                                     ▼
                  ┌─────────────────────────────────────┐
                  │  Developer 2 Evidence Builder       │
                  │  - Returns EvidenceItem List        │
                  │  - Flagged Bounding Regions         │
                  └─────────────────────────────────────┘
```

### Proposed Component Breakdown

1. **Deterministic ELA Engine (`app/modules/tampering/ela.py`)**:
   - Computes pixel-wise JPEG re-compression difference map.
   - Generates a localized 2D grayscale/RGB heatmap image.
2. **Noise Variance Analyzer (`app/modules/tampering/noise.py`)**:
   - Applies high-pass SRM filters to detect photo replacement and patch boundaries.
3. **Deep Learning Classifier / Localization Head (`app/modules/tampering/model.py`)**:
   - Uses PyTorch TruFor or ELA-ResNet18 classifier to output `tampering_score` ($0.0 \text{ to } 1.0$).
4. **Tampering Service Integrator (`app/modules/tampering/service.py`)**:
   - Merges stream outputs, generates bounding boxes around high-anomaly regions, and creates structured `EvidenceItem` records for the SIH26188 pipeline.

---

## 11. Risks and Limitations

* **Social Media Re-compression**: Images received via WhatsApp, Telegram, or heavy web compression may have high JPEG artifacts, which can elevate baseline ELA noise. *Mitigation: Normalize ELA thresholding based on estimated image JPEG quality factor.*
* **Low-Resolution Scans**: Documents under $600 \times 400$ pixels lack sufficient frequency detail for subtle text editing localization. *Mitigation: Issue a quality warning if document resolution is below threshold.*
* **Native Windows C++ Dependencies**: Heavy frameworks like MMCV require careful environment isolation. *Mitigation: Rely on native PyTorch + Torchvision + OpenCV implementations for backend stability.*

---

## 12. Final Recommendation

For immediate implementation in Developer 2 modules:

1. **Primary Prototype Engine**: Implement a hybrid **Error Level Analysis (ELA) + SRM High-Pass Noise Variance + PyTorch ResNet Baseline** in Python/PyTorch. This approach runs 100% locally on Windows/Linux CPU, requires zero complex C++ compilation, completes in $< 100\text{ms}$, and produces clear 2D heatmaps and global confidence scores.
2. **Secondary Deep Learning Extension**: Integrate pretrained **TruFor** weights as an optional GPU-accelerated deep-learning localization head for advanced photo replacement and splicing checks.
3. **Documentation & Spec Persistence**: This research report serves as the complete technical specification stored at `docs/TAMPERING_DETECTION_RESEARCH.md`.

---

## 13. References

1. **SIDTD Dataset & Codebase**: Oriol Ramos Terrades et al., *"SIDTD: Synthetic ID and Travel Documents Dataset for Forgery Detection"*, GitHub: [Oriolrt/SIDTD_Dataset](https://github.com/Oriolrt/SIDTD_Dataset).
2. **DocTamper Framework**: Chen et al., *"Towards Robust Tampered Text Detection in Document Image: New Dataset and New Solution"*, CVPR 2023, GitHub: [qcf-568/DocTamper](https://github.com/qcf-568/DocTamper).
3. **TruFor Forensic Framework**: Guillaro et al., *"TruFor: Leveraging Noise and Visual Features for Image Forgery Detection and Localization"*, CVPR 2023, GitHub: [grip-unina/TruFor](https://github.com/grip-unina/TruFor).
4. **CAT-Net (JPEG Artifact Tracing)**: Kwon et al., *"CAT-Net: Compression Artifact Tracing Network for Detection and Localization of Image Splicing"*, IEEE TIFS 2021, GitHub: [mjkwon2021/CAT-Net](https://github.com/mjkwon2021/CAT-Net).
5. **MIDV-2020 Dataset**: Arlazarov et al., *"MIDV-2020: A Dataset for Identity Document Analysis and Recognition on Mobile Devices"*, 2020.
