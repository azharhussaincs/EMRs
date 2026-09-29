from enum import Enum
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class ClinicalDomain(str, Enum):
    DIABETES = "diabetes"
    CARDIOVASCULAR = "cardiovascular"
    CHRONIC_KIDNEY_DISEASE = "chronic_kidney_disease"
    CANCER = "cancer"


class RiskTier(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Clinical EMR Generative AI Platform"
    PROJECT_VERSION: str = "0.1.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # Security & HIPAA Compliance posture
    SECRET_KEY: str = "clinical-platform-dev-insecure-secret-key-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_PATH: str = "logs/audit.log"
    PHI_MASKING_ENABLED: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Clinical Engine Configuration
    ENABLED_DOMAINS: List[ClinicalDomain] = [
        ClinicalDomain.DIABETES,
        ClinicalDomain.CARDIOVASCULAR,
        ClinicalDomain.CHRONIC_KIDNEY_DISEASE,
        ClinicalDomain.CANCER,
    ]

    # Generative AI & Knowledge Base configuration placeholders
    GENAI_PROVIDER: str = "mock"  # Configurable: "mock", "gemini", "openai", "bedrock", "local-vllm"
    GENAI_MODEL_NAME: str = "gemini-1.5-pro"
    GENAI_API_KEY: Optional[str] = None
    GENAI_API_BASE_URL: Optional[str] = None
    GENAI_TIMEOUT_SECONDS: int = 30
    GENAI_MAX_OUTPUT_TOKENS: int = 1024
    VECTOR_DB_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
