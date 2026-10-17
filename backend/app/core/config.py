import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Farm Saathi — Smart Irrigation Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "farm_saathi_super_secret_production_key_change_in_env_2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days for farmers
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # Database config: defaults to local SQLite file with WAL mode for zero friction, 
    # but immediately switches to PostgreSQL / Neon when DATABASE_URL is set!
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./farm_saathi.db")
    
    # Farm default timezone
    DEFAULT_TIMEZONE: str = os.getenv("DEFAULT_TIMEZONE", "Asia/Kolkata")
    
    # Device communication timeout in seconds (controller offline threshold)
    DEVICE_OFFLINE_THRESHOLD_SECONDS: int = 60
    
    # Command timeout in seconds
    COMMAND_TIMEOUT_SECONDS: int = 20
    
    # CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
