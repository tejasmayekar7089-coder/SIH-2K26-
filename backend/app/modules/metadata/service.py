import os
from app.schemas.document import ValidatedInputDocument
from app.schemas.metadata import MetadataResult
from app.modules.metadata.analyzer import IsolatedMetadataAnalyzer
from app.core.logging import get_logger

logger = get_logger("metadata")

class MetadataService:
    """Module 4B: Digital File Header & EXIF Metadata Analysis Service."""

    def __init__(self, analyzer: IsolatedMetadataAnalyzer = None):
        self.analyzer = analyzer or IsolatedMetadataAnalyzer()

    def extract_metadata(self, doc: ValidatedInputDocument) -> MetadataResult:
        """Analyzes uploaded document file for digital metadata supporting evidence."""
        logger.info(f"Extracting metadata for document: {doc.document_id} ({doc.storage_path})")

        return self.analyzer.analyze_file(
            file_path=doc.storage_path,
            document_id=doc.document_id
        )
