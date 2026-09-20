import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

# Detect project workspace root (where data/ and models/ reside)
CURRENT_FILE = Path(__file__).resolve()
POSSIBLE_ROOTS = [
    CURRENT_FILE.parents[3],  # AI_Student_MS root
    CURRENT_FILE.parents[2],  # backend root
    Path.cwd()
]
PROJECT_ROOT = CURRENT_FILE.parents[3]
for r in POSSIBLE_ROOTS:
    if (r / "data").exists() or (r / "models").exists():
        PROJECT_ROOT = r
        break


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Attendance & Engagement Analyzer"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = f"sqlite:///{PROJECT_ROOT}/data/database/app.db"

    # Paths
    DATA_DIR: str = str(PROJECT_ROOT / "data")
    MODELS_DIR: str = str(PROJECT_ROOT / "models")
    FACE_MODEL_PATH: str = str(PROJECT_ROOT / "models" / "yolov8n-face.pt")

    # Face Detection & Recognition
    FACE_CONFIDENCE_THRESHOLD: float = 0.50
    FACE_MATCH_THRESHOLD: float = 0.55

    # Attendance Logic
    MIN_CONFIRMATION_SECONDS: float = 2.0
    SESSION_ABSENCE_THRESHOLD_RATIO: float = 0.50

    # Engagement Scoring Weights (Orientation 50%, Visibility 30%, Presence 20%)
    ENGAGEMENT_ORIENTATION_WEIGHT: float = 0.50
    ENGAGEMENT_VISIBILITY_WEIGHT: float = 0.30
    ENGAGEMENT_PRESENCE_WEIGHT: float = 0.20

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
