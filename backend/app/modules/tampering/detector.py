import cv2
import numpy as np
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)

def run_tampering(image_path: str) -> Dict[str, Any]:
    """
    Lightweight, local tampering detection module using OpenCV.
    Designed to be drop-in replaceable with DocTamper/TruFor later.
    """
    logger.debug(f"Starting tampering detection for image: {image_path}")
    
    if not os.path.exists(image_path):
        logger.error(f"Image path does not exist: {image_path}")
        return _build_error_response("Image path does not exist")
        
    image = cv2.imread(image_path)
    if image is None:
        logger.error(f"Failed to load image: {image_path}")
        return _build_error_response("Failed to load image")
        
    # 1. Grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 2. Gaussian Blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # 3. Canny Edge Detection
    edges = cv2.Canny(blurred, 50, 150)
    
    # Calculate edge intensity for scoring
    edge_intensity = np.mean(edges) / 255.0
    logger.debug(f"Calculated edge intensity: {edge_intensity}")
    
    # Group nearby edges by dilating them
    kernel = np.ones((9, 9), np.uint8)
    dilated_edges = cv2.dilate(edges, kernel, iterations=1)
    
    # 4. Find contours of suspicious regions
    contours, _ = cv2.findContours(dilated_edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 5. Filter contours based on area threshold
    suspicious_regions = []
    min_area = 500  # Threshold can be adjusted
    
    heatmap_mask = np.zeros_like(gray, dtype=np.float32)
    
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > min_area:
            # 6. Generate bounding boxes
            x, y, w, h = cv2.boundingRect(contour)
            suspicious_regions.append({
                "x": int(x),
                "y": int(y),
                "width": int(w),
                "height": int(h),
                "area": float(area)
            })
            # Add to mask for heatmap
            cv2.drawContours(heatmap_mask, [contour], -1, 1.0, thickness=cv2.FILLED)
            
    logger.debug(f"Found {len(suspicious_regions)} suspicious regions")
            
    # Compute tamper_score based on number of regions and edge intensity
    num_regions_score = min(len(suspicious_regions) / 10.0, 1.0)
    
    tamper_score = (num_regions_score * 0.6) + (edge_intensity * 0.4)
    tamper_score = min(max(tamper_score, 0.0), 1.0)
    
    logger.debug(f"Computed tamper_score: {tamper_score}")
    
    # Classify
    if tamper_score < 0.25:
        status = "GENUINE"
        severity = "LOW"
    elif 0.25 <= tamper_score <= 0.5:
        status = "SUSPICIOUS"
        severity = "MEDIUM"
    else:
        status = "HIGHLY SUSPICIOUS"
        severity = "HIGH"
        
    # Generate heatmap image
    heatmap_path = f"{os.path.splitext(image_path)[0]}_heatmap.jpg"
    
    # Normalize mask and apply colormap
    heatmap_normalized = np.uint8(255 * heatmap_mask)
    heatmap_color = cv2.applyColorMap(heatmap_normalized, cv2.COLORMAP_JET)
    
    # Overlay heatmap on original image
    heatmap_overlay = cv2.addWeighted(image, 0.6, heatmap_color, 0.4, 0)
    
    # Draw bounding boxes on heatmap overlay for clarity
    for region in suspicious_regions:
        x, y, w, h = region['x'], region['y'], region['width'], region['height']
        cv2.rectangle(heatmap_overlay, (x, y), (x + w, y + h), (0, 0, 255), 2)
        
    cv2.imwrite(heatmap_path, heatmap_overlay)
    logger.debug(f"Saved heatmap to: {heatmap_path}")
    
    # Compute a basic confidence metric
    if status == "SUSPICIOUS":
        confidence = 1.0 - abs(tamper_score - 0.5) * 2
    elif status == "GENUINE":
        confidence = 1.0 - tamper_score
    else:
        confidence = tamper_score
    
    result = {
        "tamper_score": float(tamper_score),
        "status": status,
        "severity": severity,
        "regions": suspicious_regions,
        "confidence": float(confidence),
        "heatmap_path": heatmap_path
    }
    
    logger.info(f"Tampering detection completed with status: {status}, score: {tamper_score}")
    return result

def _build_error_response(message: str) -> Dict[str, Any]:
    return {
        "tamper_score": 0.0,
        "status": "ERROR",
        "severity": "UNKNOWN",
        "regions": [],
        "confidence": 0.0,
        "heatmap_path": "",
        "error": message
    }
