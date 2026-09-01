import os
import cv2
import numpy as np

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def create_genuine_document(output_path: str) -> np.ndarray:
    """Generates a clean synthetic identity document specimen."""
    img = np.ones((500, 800, 3), dtype=np.uint8) * 245
    
    # Outer border and inner frame
    cv2.rectangle(img, (20, 20), (780, 480), (40, 40, 40), 2)
    cv2.rectangle(img, (25, 25), (775, 475), (180, 180, 180), 1)

    # Document Header
    cv2.putText(img, "SPECIMEN IDENTITY CARD", (220, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (10, 30, 100), 2)
    cv2.putText(img, "UNION REPUBLIC AUTHORITY", (260, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 100, 100), 1)

    # Simulated Holder Photo Region (Blue jacket on gray background)
    photo = np.ones((160, 130, 3), dtype=np.uint8) * 210
    # Head & torso shapes
    cv2.circle(photo, (65, 55), 35, (150, 120, 90), -1) # Head
    cv2.ellipse(photo, (65, 140), (50, 40), 0, 0, 180, (40, 60, 140), -1) # Torso
    img[120:280, 50:180] = photo
    cv2.rectangle(img, (50, 120), (180, 280), (50, 50, 50), 2)

    # Text Fields
    cv2.putText(img, "ID NUMBER : A123456789", (220, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(img, "NAME      : ALEX SAMPLE", (220, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(img, "DOB       : 15/08/1990", (220, 220), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(img, "SEX       : M", (220, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)
    cv2.putText(img, "EXPIRY    : 15/08/2030", (220, 300), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (20, 20, 20), 2)

    # Security Fine Lines / Micro-text background texture
    for y in range(340, 460, 12):
        cv2.line(img, (40, y), (760, y), (220, 220, 240), 1)

    cv2.putText(img, "I<SAMPLE<<ALEX<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<", (40, 410), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 1)
    cv2.putText(img, "A1234567890XXX9008151M3008155<<<<<<<<<<<<<<02", (40, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (10, 10, 10), 1)

    # Save as high-quality initial JPEG to simulate camera upload
    cv2.imwrite(output_path, img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return img

def create_tampered_documents(genuine_path: str, out_dir: str):
    """Creates multiple synthetic manipulation specimens from genuine image."""
    base_img = cv2.imread(genuine_path)
    h, w, _ = base_img.shape

    # 1. Tampering Type A: Edited Text / DOB Alteration
    dob_edited = base_img.copy()
    # Mask out DOB region with background color
    cv2.rectangle(dob_edited, (350, 205), (550, 230), (245, 245, 245), -1)
    # Overwrite with modified year in a different font style & high contrast
    cv2.putText(dob_edited, "15/08/1998", (350, 222), cv2.FONT_HERSHEY_DUPLEX, 0.65, (0, 0, 0), 2)
    cv2.imwrite(os.path.join(out_dir, "tampered_text_edit.jpg"), dob_edited, [cv2.IMWRITE_JPEG_QUALITY, 75])

    # 2. Tampering Type B: Photo Replacement / Splicing
    photo_spliced = base_img.copy()
    # Create fake replacement photo patch (Different lighting, high noise)
    fake_photo = np.random.randint(50, 200, (160, 130, 3), dtype=np.uint8)
    cv2.circle(fake_photo, (65, 55), 35, (200, 160, 120), -1) # Different skin tone
    cv2.rectangle(fake_photo, (10, 10), (120, 150), (255, 0, 0), 2) # Red border patch
    photo_spliced[120:280, 50:180] = fake_photo
    cv2.imwrite(os.path.join(out_dir, "tampered_photo_replacement.jpg"), photo_spliced, [cv2.IMWRITE_JPEG_QUALITY, 80])

    # 3. Tampering Type C: Copy-Move Manipulation (Duplicating ID numbers)
    copy_moved = base_img.copy()
    # Copy ID Number region 'A123456789' and paste over expiry date
    id_crop = base_img[125:148, 350:520].copy()
    copy_moved[285:308, 350:520] = id_crop
    cv2.imwrite(os.path.join(out_dir, "tampered_copy_move.jpg"), copy_moved, [cv2.IMWRITE_JPEG_QUALITY, 82])

    # 4. Tampering Type D: Generative Inpainting / Text Removal
    inpainted = base_img.copy()
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.rectangle(mask, (350, 165), (550, 190), 255, -1) # Name region mask
    inpainted_res = cv2.inpaint(inpainted, mask, 3, cv2.INPAINT_TELEA)
    cv2.imwrite(os.path.join(out_dir, "tampered_inpainting.jpg"), inpainted_res, [cv2.IMWRITE_JPEG_QUALITY, 85])

if __name__ == "__main__":
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    ensure_dir(data_dir)
    
    gen_path = os.path.join(data_dir, "genuine_specimen.jpg")
    print(f"[GENERATE] Creating genuine synthetic document specimen: {gen_path}")
    create_genuine_document(gen_path)
    
    print(f"[GENERATE] Generating synthetic forgery specimens (Text Edit, Photo Replacement, Copy-Move, Inpainting)...")
    create_tampered_documents(gen_path, data_dir)
    print(f"[GENERATE] Done. Datasets created in: {data_dir}")
