import os
from typing import List
from pydantic import Field

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class Settings(BaseSettings):
        PROJECT_NAME: str = "SIH26188 — AI-Based Fake Identity & Document Screening System"
        VERSION: str = "1.0.0-hackathon-prototype"
        API_V1_STR: str = "/api/v1"
        ENVIRONMENT: str = "development"
        DEBUG: bool = True
        DOCUMENT_VALIDATION_MODE: str = os.getenv("DOCUMENT_VALIDATION_MODE", "production")
        
        # Server
        HOST: str = "0.0.0.0"
        PORT: int = 8000
        CORS_ORIGINS: List[str] = [
            "http://localhost:3000",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8501",
        ]
        
        # Storage Paths
        BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        UPLOAD_DIR: str = os.path.join(BASE_DIR, "data", "uploads")
        OUTPUT_DIR: str = os.path.join(BASE_DIR, "data", "outputs")
        MOCK_DB_PATH: str = os.path.join(BASE_DIR, "database", "mock_intelligence.db")
        AUDIT_DB_PATH: str = os.path.join(BASE_DIR, "database", "screening_audit.db")
        DATABASE_URL: str = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'database', 'screening_audit.db')}"

        # Constraints
        MAX_UPLOAD_SIZE_MB: int = 100
        ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/tiff", "image/webp", "application/pdf"]
        
        # Model Paths
        DOCTAMPER_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "doctamper", "doctamper_base.onnx")
        TRUFOR_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "trufor", "trufor_baseline.onnx")
        FACE_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "face", "arcface_r100.onnx")
        
        # Algorithmic Thresholds
        QUALITY_MIN_SCORE: float = 0.60
        FACE_MATCH_THRESHOLD: float = 0.65
        TAMPER_ALERT_THRESHOLD: float = 0.35
        TAMPER_HIGH_RISK_THRESHOLD: float = 0.70
        TAMPER_ELA_QUALITY: int = 90
        TAMPER_SRM_WEIGHT: float = 0.40
        TAMPER_CONTOUR_MIN_AREA: int = 150
        RISK_THRESHOLD_CLEAR: int = 29
        RISK_THRESHOLD_REVIEW: int = 69
        
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=True,
            extra="allow"
        )
except ImportError:
    from pydantic import BaseModel
    class Settings(BaseModel):
        PROJECT_NAME: str = "SIH26188 — AI-Based Fake Identity & Document Screening System"
        VERSION: str = "1.0.0-hackathon-prototype"
        API_V1_STR: str = "/api/v1"
        ENVIRONMENT: str = "development"
        DEBUG: bool = True
        DOCUMENT_VALIDATION_MODE: str = os.getenv("DOCUMENT_VALIDATION_MODE", "production")

        # Server
        HOST: str = "0.0.0.0"
        PORT: int = 8000
        CORS_ORIGINS: List[str] = [
            "http://localhost:3000",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8501",
        ]
        
        # Storage Paths
        BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
        UPLOAD_DIR: str = os.path.join(BASE_DIR, "data", "uploads")
        OUTPUT_DIR: str = os.path.join(BASE_DIR, "data", "outputs")
        MOCK_DB_PATH: str = os.path.join(BASE_DIR, "database", "mock_intelligence.db")
        AUDIT_DB_PATH: str = os.path.join(BASE_DIR, "database", "screening_audit.db")
        DATABASE_URL: str = f"sqlite+aiosqlite:///{os.path.join(BASE_DIR, 'database', 'screening_audit.db')}"

        # Constraints
        MAX_UPLOAD_SIZE_MB: int = 100
        ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/tiff", "image/webp", "application/pdf"]
        
        # Model Paths
        DOCTAMPER_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "doctamper", "doctamper_base.onnx")
        TRUFOR_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "trufor", "trufor_baseline.onnx")
        FACE_MODEL_PATH: str = os.path.join(BASE_DIR, "models", "face", "arcface_r100.onnx")
        
        # Algorithmic Thresholds
        QUALITY_MIN_SCORE: float = 0.60
        FACE_MATCH_THRESHOLD: float = 0.65
        TAMPER_ALERT_THRESHOLD: float = 0.35
        TAMPER_HIGH_RISK_THRESHOLD: float = 0.70
        TAMPER_ELA_QUALITY: int = 90
        TAMPER_SRM_WEIGHT: float = 0.40
        TAMPER_CONTOUR_MIN_AREA: int = 150
        RISK_THRESHOLD_CLEAR: int = 29
        RISK_THRESHOLD_REVIEW: int = 69

settings = Settings()

# Ensure runtime directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.AUDIT_DB_PATH), exist_ok=True)
