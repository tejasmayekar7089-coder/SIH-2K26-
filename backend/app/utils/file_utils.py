import os
import hashlib
from app.schemas.document import FileFormat

def detect_file_format(filename: str) -> FileFormat:
    """Determine FileFormat from file extension."""
    ext = os.path.splitext(filename)[1].lower().strip(".")
    if ext == "pdf":
        return FileFormat.PDF
    elif ext in ["jpg", "jpeg"]:
        return FileFormat.JPG
    elif ext == "png":
        return FileFormat.PNG
    elif ext == "tiff":
        return FileFormat.TIFF
    elif ext == "webp":
        return FileFormat.WEBP
    return FileFormat.JPG

def get_mime_type(file_format: FileFormat) -> str:
    """Map FileFormat to MIME string."""
    mapping = {
        FileFormat.PDF: "application/pdf",
        FileFormat.JPG: "image/jpeg",
        FileFormat.JPEG: "image/jpeg",
        FileFormat.PNG: "image/png",
        FileFormat.TIFF: "image/tiff",
        FileFormat.WEBP: "image/webp",
    }
    return mapping.get(file_format, "application/octet-stream")

def save_uploaded_bytes(content: bytes, destination_path: str) -> str:
    """Safely persist byte stream to disk."""
    os.makedirs(os.path.dirname(destination_path), exist_ok=True)
    with open(destination_path, "wb") as f:
        f.write(content)
    return destination_path

def compute_sha256(file_path: str) -> str:
    """Computes SHA-256 hash digest of a file on disk."""
    if not os.path.exists(file_path):
        return "0" * 64
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()
