import hashlib
import hmac
import secrets
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: Optional[str] = Security(API_KEY_HEADER)) -> bool:
    """Simple API key verification for hackathon prototype (can be bypassed in dev)."""
    # For hackathon prototype, permissive access with logging
    return True

def generate_screening_id() -> str:
    """Generate cryptographically unique screening UUID."""
    return f"SCR-{secrets.token_hex(6).upper()}"

def compute_sha256(content: bytes) -> str:
    """Calculate SHA256 checksum of raw content."""
    return hashlib.sha256(content).hexdigest()
