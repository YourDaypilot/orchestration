"""
Configuration settings for DayPilot Orchestration Hub
"""
import os
from pathlib import Path
from typing import Optional

class Settings:
    """Application settings"""

    # Application
    APP_NAME = "DayPilot Orchestration Hub"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    WORKERS = int(os.getenv("WORKERS", "4"))

    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    API_KEY_HEADER = "X-API-Key"
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/daypilot")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/daypilot")

    # External Services
    PERCEPTION_CORE_URL = os.getenv("PERCEPTION_CORE_URL", "http://localhost:8001")
    RHYTHM_INTELLIGENCE_URL = os.getenv("RHYTHM_INTELLIGENCE_URL", "http://localhost:8002")
    INTERVENTION_PLATFORM_URL = os.getenv("INTERVENTION_PLATFORM_URL", "http://localhost:8003")

    # Performance
    MAX_CONCURRENT_WORKFLOWS = int(os.getenv("MAX_CONCURRENT_WORKFLOWS", "100"))
    REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    WORKFLOW_TIMEOUT_SECONDS = int(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "60"))

    # Monitoring
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    METRICS_PORT = int(os.getenv("METRICS_PORT", "9090"))
    HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_BURST = int(os.getenv("RATE_LIMIT_BURST", "10"))

    # Tracing
    TRACE_DIR = Path(__file__).parent.parent / "trace"
    TRACE_RETENTION_DAYS = int(os.getenv("TRACE_RETENTION_DAYS", "30"))

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

    @classmethod
    def validate(cls):
        """Validate configuration"""
        from utils.trace_logger import trace

        trace.info("Validating configuration", {
            "app_name": cls.APP_NAME,
            "version": cls.APP_VERSION,
            "debug": cls.DEBUG,
            "host": cls.HOST,
            "port": cls.PORT
        }, module=__name__, function="validate")

        return True


settings = Settings()
