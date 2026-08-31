-- SIH26188 Schema Definition (SQLite & PostgreSQL Compatible)

-- Screenings & Audit Log Table
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

-- Mock External Intelligence Watchlist Table
CREATE TABLE IF NOT EXISTS mock_registry (
    document_number TEXT PRIMARY KEY,
    country_code TEXT NOT NULL,
    holder_name TEXT NOT NULL,
    status TEXT NOT NULL,
    issue_date TEXT,
    expiry_date TEXT,
    remarks TEXT
);

CREATE INDEX IF NOT EXISTS idx_screenings_time ON screenings(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_screenings_risk ON screenings(risk_level);
