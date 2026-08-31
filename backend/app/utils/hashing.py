import hashlib
import json
from typing import Any, Dict

def hash_bytes(data: bytes) -> str:
    """Compute hex SHA-256 for binary content."""
    return hashlib.sha256(data).hexdigest()

def hash_file(file_path: str) -> str:
    """Compute SHA-256 for a file on disk."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def hash_dict(payload: Dict[str, Any]) -> str:
    """Compute deterministic SHA-256 for a JSON serializable dict."""
    encoded = json.dumps(payload, sort_keys=True, default=str).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()
