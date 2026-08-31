#!/usr/bin/env python3
"""
SIH26188 Setup & Verification Script
Prepares environment directories, SQLite databases, and model folders.
"""
import os
import sys
import sqlite3

def run_setup():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print(f"[*] Setting up SIH26188 Document Screening System at: {base_dir}")

    # 1. Ensure all directories exist
    dirs = [
        "data/uploads",
        "data/outputs",
        "data/samples",
        "data/synthetic",
        "data/test_cases",
        "models/doctamper",
        "models/trufor",
        "models/face",
        "database",
        "docs/architecture",
        "docs/api",
        "docs/module_specs",
        "docs/testing"
    ]
    for d in dirs:
        full_p = os.path.join(base_dir, d)
        os.makedirs(full_p, exist_ok=True)
        print(f"  [+] Directory verified: {d}")

    # 2. Initialize and Seed Mock Database
    db_path = os.path.join(base_dir, "database", "mock_intelligence.db")
    schema_path = os.path.join(base_dir, "database", "schema.sql")
    seed_path = os.path.join(base_dir, "database", "mock_data.sql")

    print("[*] Initializing mock registry database...")
    with sqlite3.connect(db_path) as conn:
        if os.path.exists(schema_path):
            with open(schema_path, "r") as f:
                conn.executescript(f.read())
        if os.path.exists(seed_path):
            with open(seed_path, "r") as f:
                conn.executescript(f.read())
        conn.commit()
    print("  [+] Mock registry SQLite database seeded successfully.")

    print("\n[OK] SIH26188 environment setup complete.")
    print("     Start backend with: uvicorn app.main:app --reload (from backend/)")

if __name__ == "__main__":
    run_setup()
