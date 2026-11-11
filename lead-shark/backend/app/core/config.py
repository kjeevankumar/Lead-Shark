import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "LEAD SHARK"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Database
    # Support Supabase PostgreSQL or fallback to SQLite for local development
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./lead_shark.db"
    )
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "leadshark-super-secret-production-grade-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    
    # CORS
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "*")
    
    @property
    def cors_origins(self) -> List[str]:
        if self.FRONTEND_ORIGIN == "*":
            return ["*"]
        return [origin.strip() for origin in self.FRONTEND_ORIGIN.split(",") if origin.strip()]
        
    # RAG Lead Segregation Agent
    RAG_AGENT_URL: str = os.getenv("RAG_AGENT_URL", "")
    
    # Universal Lead Discovery External Provider Keys (Optional)
    GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
    SERPER_API_KEY: str = os.getenv("SERPER_API_KEY", "")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")
    BRAVE_SEARCH_API_KEY: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
    DISCOVERY_HTTP_TIMEOUT: float = float(os.getenv("DISCOVERY_HTTP_TIMEOUT", "8.0"))
    DISCOVERY_CACHE_TTL_SECONDS: int = int(os.getenv("DISCOVERY_CACHE_TTL_SECONDS", "600"))
    
    # Email & Sending Settings
    SENDING_MODE: str = os.getenv("SENDING_MODE", "safe_demo") # safe_demo | live_provider
    SENDING_DOMAIN: str = os.getenv("SENDING_DOMAIN", "mail.leadshark.io")
    COMPANY_POSTAL_ADDRESS: str = os.getenv(
        "COMPANY_POSTAL_ADDRESS", 
        "100 Innovation Way, Suite 500, Tech District, CA 94105, USA"
    )
    EMAIL_PROVIDER_API_KEY: str = os.getenv("EMAIL_PROVIDER_API_KEY", "")
    
    # Compliance rules
    COOLDOWN_DAYS: int = 30
    MAX_BOUNCE_RATE_PERCENT: float = 3.0
    MAX_COMPLAINT_RATE_PERCENT: float = 0.1
    
    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()
