import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import ConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.path.join(BACKEND_DIR, "medislot.db").replace("\\", "/")

class Settings(BaseSettings):
    PROJECT_NAME: str = "MediSlot"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-medislot-production-key-change-in-env-32bytes!")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database (Default absolute path to backend/medislot.db)
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Gemini AI
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Platform Behavior
    SINGLE_HOSPITAL_MODE: bool = os.getenv("SINGLE_HOSPITAL_MODE", "false").lower() == "true"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    model_config = ConfigDict(env_file=".env", extra="allow")

settings = Settings()
