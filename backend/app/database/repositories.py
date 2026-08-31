import json
import sqlite3
import asyncio
from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.schemas.screening import ScreeningResponse, OfficerAction
from app.schemas.audit import AuditLogEntry

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

class ScreeningRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.AUDIT_DB_PATH

    async def save_screening(self, screening: ScreeningResponse) -> None:
        """Insert or replace screening execution log."""
        reasons_str = json.dumps(screening.risk_assessment.top_reasons) if screening.risk_assessment else "[]"
        bundle_str = screening.evidence_bundle.model_dump_json() if screening.evidence_bundle else "{}"
        
        params = (
            screening.screening_id,
            screening.timestamp_utc.isoformat(),
            screening.document_info.document_id if screening.document_info else "DOC-UNKNOWN",
            screening.document_info.file_name if screening.document_info else "unknown",
            screening.document_info.sha256_checksum if screening.document_info else "",
            screening.risk_assessment.risk_level.value if screening.risk_assessment else "REVIEW",
            screening.risk_assessment.risk_score if screening.risk_assessment else 50,
            reasons_str,
            screening.officer_action_state.value,
            None,
            screening.processing_time_ms,
            bundle_str
        )

        def _sync_save():
            with sqlite3.connect(self.db_path) as db:
                db.execute("""
                    INSERT OR REPLACE INTO screenings (
                        screening_id, timestamp_utc, document_id, file_name,
                        sha256_checksum, risk_level, risk_score, top_reasons,
                        officer_action, officer_notes, processing_time_ms, evidence_bundle_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, params)
                db.commit()

        if HAS_AIOSQLITE:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO screenings (
                        screening_id, timestamp_utc, document_id, file_name,
                        sha256_checksum, risk_level, risk_score, top_reasons,
                        officer_action, officer_notes, processing_time_ms, evidence_bundle_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, params)
                await db.commit()
        else:
            await asyncio.to_thread(_sync_save)

    async def update_officer_action(self, screening_id: str, action: OfficerAction, notes: str) -> bool:
        """Update screening record with human officer adjudication."""
        def _sync_update():
            with sqlite3.connect(self.db_path) as db:
                cursor = db.execute("""
                    UPDATE screenings
                    SET officer_action = ?, officer_notes = ?
                    WHERE screening_id = ?
                """, (action.value, notes, screening_id))
                db.commit()
                return cursor.rowcount > 0

        if HAS_AIOSQLITE:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    UPDATE screenings
                    SET officer_action = ?, officer_notes = ?
                    WHERE screening_id = ?
                """, (action.value, notes, screening_id))
                await db.commit()
                return cursor.rowcount > 0
        else:
            return await asyncio.to_thread(_sync_update)

    async def get_screening_by_id(self, screening_id: str) -> Optional[Dict[str, Any]]:
        """Fetch raw record by screening ID."""
        def _sync_get():
            with sqlite3.connect(self.db_path) as db:
                db.row_factory = sqlite3.Row
                cursor = db.execute("SELECT * FROM screenings WHERE screening_id = ?", (screening_id,))
                row = cursor.fetchone()
                if row:
                    return dict(row)
                return None

        if HAS_AIOSQLITE:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM screenings WHERE screening_id = ?", (screening_id,))
                row = await cursor.fetchone()
                if row:
                    return dict(row)
                return None
        else:
            return await asyncio.to_thread(_sync_get)
