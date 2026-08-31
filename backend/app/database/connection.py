import os
import asyncio
import sqlite3
from app.core.config import settings

try:
    import aiosqlite
    HAS_AIOSQLITE = True
except ImportError:
    HAS_AIOSQLITE = False

async def init_db():
    """Initialize database tables if not existing."""
    db_path = settings.AUDIT_DB_PATH
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    def _sync_init():
        with sqlite3.connect(db_path) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS screenings (
                    screening_id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    sha256_checksum TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    top_reasons TEXT,
                    officer_action TEXT DEFAULT 'PENDING',
                    officer_notes TEXT,
                    processing_time_ms REAL,
                    evidence_bundle_json TEXT
                );
            """)
            db.commit()

    if HAS_AIOSQLITE:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS screenings (
                    screening_id TEXT PRIMARY KEY,
                    timestamp_utc TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    sha256_checksum TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    risk_score INTEGER NOT NULL,
                    top_reasons TEXT,
                    officer_action TEXT DEFAULT 'PENDING',
                    officer_notes TEXT,
                    processing_time_ms REAL,
                    evidence_bundle_json TEXT
                );
            """)
            await db.commit()
    else:
        await asyncio.to_thread(_sync_init)
