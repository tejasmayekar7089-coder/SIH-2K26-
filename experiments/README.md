# SIH26188 Document Tampering Detection Experiments

This directory contains reproducible experimental code and synthetic test specimens for evaluating document image tampering detection models.

## Structure

```
experiments/
├── README.md                          # This reproducibility guide
├── generate_test_tampering.py         # Synthetic specimen generator (Genuine + Tampered)
├── test_inference.py                  # Practical model inference benchmarking script
└── data/                              # Generated synthetic document test images
    ├── genuine_specimen.jpg
    ├── tampered_text_edit.jpg
    ├── tampered_photo_replacement.jpg
    ├── tampered_copy_move.jpg
    └── tampered_inpainting.jpg
```

## How to Reproduce Experiments

### 1. Generate Synthetic Specimens
```powershell
$env:PYTHONPATH="backend"
.venv\Scripts\python.exe experiments/generate_test_tampering.py
```

### 2. Run Tampering Detection Inference Benchmark
```powershell
$env:PYTHONPATH="backend"
.venv\Scripts\python.exe experiments/test_inference.py
```

## Evaluated Models & Approaches
1. **Signal Multi-Stream Analyzer (ELA + SRM High-Pass Noise Variance)**: Fast, zero-weight, CPU-native localized heatmap and bounding box generator.
2. **PyTorch DL ResNet18 ELA Classifier**: Fine-grained feature classification network.
3. **DocTamper DTD / SegFormer**: Text tampering localization benchmark.
4. **TruFor Framework**: Transformer-based RGB + Noiseprint++ forgery detector.
