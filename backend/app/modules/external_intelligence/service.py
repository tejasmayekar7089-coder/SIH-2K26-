import os
import sqlite3
from typing import Optional
from app.schemas.extraction import ExtractionResult
from app.schemas.database import DatabaseResult, RegistryStatus
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("external_intelligence")

class ExternalIntelligenceService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.MOCK_DB_PATH
        self._ensure_mock_db()

    def _ensure_mock_db(self):
        """Create mock database schema if not present."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mock_registry (
                    document_number TEXT PRIMARY KEY,
                    country_code TEXT,
                    holder_name TEXT,
                    status TEXT,
                    issue_date TEXT,
                    expiry_date TEXT,
                    remarks TEXT
                );
            """)
            # Insert standard simulated test records if empty
            cursor = conn.execute("SELECT COUNT(*) FROM mock_registry")
            if cursor.fetchone()[0] == 0:
                conn.executemany("""
                    INSERT INTO mock_registry VALUES (?, ?, ?, ?, ?, ?, ?)
                """, [
                    ("P8923412", "IND", "SHARMA, ARJUN", "VALID", "2022-05-14", "2032-05-13", "Simulated active passport"),
                    ("P9999999", "IND", "DOE, JOHN", "STOLEN", "2020-01-01", "2030-01-01", "Simulated lost/stolen passport alert"),
                    ("W1234567", "IND", "BAD_ACTOR, TEST", "WATCHLIST", "2019-03-10", "2029-03-09", "Simulated security watchlist hit")
                ])
                conn.commit()

    def query_document_status(self, extraction: ExtractionResult) -> DatabaseResult:
        """Module 9: Mock External Intelligence Database Query."""
        logger.info("Executing simulated external intelligence query")
        
        doc_no = extraction.document_number.value if extraction.document_number else None
        if not doc_no:
            return DatabaseResult(status=RegistryStatus.NOT_FOUND)

        cleaned_doc_no = doc_no.strip().replace(" ", "")
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM mock_registry WHERE document_number = ?", (cleaned_doc_no,))
            row = cursor.fetchone()
            
            if row:
                raw_status = row["status"].upper()
                status_enum = RegistryStatus.VALID
                if raw_status == "STOLEN":
                    status_enum = RegistryStatus.STOLEN
                elif raw_status == "LOST":
                    status_enum = RegistryStatus.LOST
                elif raw_status == "WATCHLIST":
                    status_enum = RegistryStatus.WATCHLIST
                elif raw_status == "REVOKED":
                    status_enum = RegistryStatus.REVOKED
                elif raw_status == "EXPIRED":
                    status_enum = RegistryStatus.EXPIRED

                return DatabaseResult(
                    is_simulated_data=True,
                    document_number_queried=cleaned_doc_no,
                    status=status_enum,
                    issuer_country=row["country_code"],
                    issue_date=row["issue_date"],
                    expiry_date=row["expiry_date"],
                    remarks=row["remarks"]
                )

        # Default fallback for unlisted document in prototype
        return DatabaseResult(
            is_simulated_data=True,
            document_number_queried=cleaned_doc_no,
            status=RegistryStatus.VALID,
            remarks="Simulated record (Mock DB auto-resolved)."
        )
