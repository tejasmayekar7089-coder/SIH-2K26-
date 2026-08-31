import hashlib
from typing import Dict, Any, Optional, Tuple, Union
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("fixture_registry")

# Registered development test fixtures identified strictly by file SHA-256 hash.
# Arbitrary documents with similar names/fields will NOT match.
REGISTERED_FIXTURES: Dict[str, Dict[str, Any]] = {
    "f9b8a8df46443d1a0158958a3a3e55debcfe54c5676b19675101232d0e9d04a2": {
        "fixture_id": "SYNTH_PASSPORT_DEMO_01",
        "title": "Synthetic Indian Passport Demo Specimen",
        "expected_document_type": "PASSPORT",
        "holder_name": "Rahul Sharma",
        "document_number": "Z1234567",
        "description": "Registered development test specimen with synthetic ICAO 9303 MRZ payload.",
        "created_for": "SIH26188 Development & Demonstration Pipeline"
    }
}

class TestFixtureRegistry:
    """Deterministic Registry for Development Test Fixtures."""

    @staticmethod
    def compute_sha256(input_data: Union[str, bytes]) -> str:
        """Computes SHA-256 hash from file path or raw bytes."""
        hasher = hashlib.sha256()
        if isinstance(input_data, str):
            with open(input_data, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
        elif isinstance(input_data, bytes):
            hasher.update(input_data)
        return hasher.hexdigest().lower()

    @classmethod
    def is_fixture_mode_enabled(cls) -> bool:
        """Checks if application is in development/test validation mode."""
        mode = getattr(settings, "DOCUMENT_VALIDATION_MODE", "production").strip().lower()
        return mode in ("development", "test", "demo", "dev")

    @classmethod
    def lookup_fixture(cls, input_data: Union[str, bytes]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Determines whether the document matches a registered fixture SHA-256.
        Returns (is_fixture, fixture_metadata).
        """
        try:
            sha256_hash = cls.compute_sha256(input_data)
            if sha256_hash in REGISTERED_FIXTURES:
                fixture_meta = REGISTERED_FIXTURES[sha256_hash]
                logger.info(f"Matched registered test fixture: {fixture_meta['fixture_id']} (SHA256: {sha256_hash[:12]}...)")
                return True, fixture_meta
            return False, None
        except Exception as e:
            logger.warning(f"Error checking fixture registry: {e}")
            return False, None
