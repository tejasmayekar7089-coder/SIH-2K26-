import os
import tempfile
import pytest
from PIL import Image

from app.core.config import settings
from app.modules.fixtures.registry import TestFixtureRegistry, REGISTERED_FIXTURES
from app.modules.document_intelligence.pipeline import DocumentIntelligencePipeline
from app.schemas.validation import RuleStatus

@pytest.fixture
def synthetic_passport_fixture():
    """Provides path to the registered synthetic test specimen image."""
    path = os.path.join(settings.UPLOAD_DIR, "DOC-3F44A169_ChatGPT Image Aug 31, 2026, 03_40_59 PM.png")
    if not os.path.exists(path):
        pytest.skip("Synthetic passport test specimen file not found in upload directory.")
    return path

@pytest.fixture
def random_invalid_doc():
    """Creates a temporary random invalid image for testing fixture isolation."""
    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "test_random_invalid_specimen.png")
    img = Image.new("RGB", (300, 150), color=(120, 50, 50))
    img.save(path)
    yield path
    if os.path.exists(path):
        os.remove(path)

def test_fixture_hash_calculation(synthetic_passport_fixture):
    """Verify SHA-256 calculation for registered fixture."""
    sha256 = TestFixtureRegistry.compute_sha256(synthetic_passport_fixture)
    assert sha256 in REGISTERED_FIXTURES
    fixture_info = REGISTERED_FIXTURES[sha256]
    assert fixture_info["fixture_id"] == "SYNTH_PASSPORT_DEMO_01"

def test_a_synthetic_fixture_in_development_mode(synthetic_passport_fixture):
    """
    Test A: Synthetic fixture + DOCUMENT_VALIDATION_MODE=development
    Must return validation_mode='TEST_FIXTURE', is_synthetic_fixture=True, overall_status='PASS'.
    """
    original_mode = settings.DOCUMENT_VALIDATION_MODE
    try:
        settings.DOCUMENT_VALIDATION_MODE = "development"
        pipeline = DocumentIntelligencePipeline()
        result = pipeline.process_document(synthetic_passport_fixture)

        assert result.validation_mode == "TEST_FIXTURE"
        assert result.is_synthetic_fixture is True
        assert result.validation.overall_status == RuleStatus.PASS
        assert result.validation.validation_mode == "TEST_FIXTURE"
        assert result.validation.is_synthetic_fixture is True
        assert result.validation.fixture_id == "SYNTH_PASSPORT_DEMO_01"
        assert result.validation.raw_validation_status is not None
        assert result.fixture_info is not None
    finally:
        settings.DOCUMENT_VALIDATION_MODE = original_mode

def test_b_synthetic_fixture_in_production_mode(synthetic_passport_fixture):
    """
    Test B: Synthetic fixture + DOCUMENT_VALIDATION_MODE=production
    Must run strict validation and NOT override to TEST_FIXTURE.
    """
    original_mode = settings.DOCUMENT_VALIDATION_MODE
    try:
        settings.DOCUMENT_VALIDATION_MODE = "production"
        pipeline = DocumentIntelligencePipeline()
        result = pipeline.process_document(synthetic_passport_fixture)

        assert result.validation_mode == "STRICT"
        assert result.is_synthetic_fixture is False
        assert result.validation.validation_mode == "STRICT"
        assert result.validation.is_synthetic_fixture is False
        # Raw strict status is preserved without fixture override
    finally:
        settings.DOCUMENT_VALIDATION_MODE = original_mode

def test_c_random_invalid_document_not_accepted_as_fixture(random_invalid_doc):
    """
    Test C: Random invalid passport/document in development mode
    Must NOT be accepted as a test fixture.
    """
    original_mode = settings.DOCUMENT_VALIDATION_MODE
    try:
        settings.DOCUMENT_VALIDATION_MODE = "development"
        pipeline = DocumentIntelligencePipeline()
        result = pipeline.process_document(random_invalid_doc)

        assert result.validation_mode == "STRICT"
        assert result.is_synthetic_fixture is False
        assert result.validation.is_synthetic_fixture is False
        assert result.fixture_info is None
    finally:
        settings.DOCUMENT_VALIDATION_MODE = original_mode

def test_d_normal_document_validation_path(random_invalid_doc):
    """
    Test D: Normal document evaluation path handles non-fixtures normally.
    """
    original_mode = settings.DOCUMENT_VALIDATION_MODE
    try:
        settings.DOCUMENT_VALIDATION_MODE = "development"
        is_fixture, meta = TestFixtureRegistry.lookup_fixture(random_invalid_doc)
        assert is_fixture is False
        assert meta is None
    finally:
        settings.DOCUMENT_VALIDATION_MODE = original_mode
