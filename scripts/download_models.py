#!/usr/bin/env python3
"""
Model weights downloader script (Pretrained Baselines)
Prepares model weights for DocTamper/DTD, TruFor, and InsightFace/ArcFace.
"""
import os

def check_models():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    models_dir = os.path.join(base_dir, "models")
    
    targets = [
        os.path.join(models_dir, "doctamper", "doctamper_base.onnx"),
        os.path.join(models_dir, "trufor", "trufor_baseline.onnx"),
        os.path.join(models_dir, "face", "arcface_r100.onnx")
    ]
    
    print("[*] Checking Pretrained Model Weight Checkpoints:")
    for t in targets:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        if os.path.exists(t):
            print(f"  [OK] Model found: {t}")
        else:
            print(f"  [-] Model checkpoint placeholder ready for weights: {t}")

if __name__ == "__main__":
    check_models()
