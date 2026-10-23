

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "testing", "production"]


class Settings(BaseSettings):
    

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    
    
    
    APP_NAME: str = "College Library Management System"
    ENVIRONMENT: Environment = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api"
    APP_BASE_URL: str = "http://localhost:5173"
    FRONTEND_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    LIBRARY_TIMEZONE: str = "Asia/Kolkata"

    
    
    
    DATABASE_URL: str = Field(
        default="mysql+pymysql://library:library@localhost:3306/library_db?charset=utf8mb4"
    )
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800

    
    
    
    SECRET_KEY: str = "CHANGE_ME_super_secret_key_generate_with_openssl_rand_hex_32"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    EMAIL_VERIFICATION_EXPIRE_HOURS: int = 24
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"
    REFRESH_COOKIE_NAME: str = "library_refresh_token"
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    
    
    
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "library@example.edu"
    SMTP_FROM_NAME: str = "College Library"
    SMTP_STARTTLS: bool = False
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 30
    
    
    EMAIL_BACKEND: Literal["smtp", "mock", "console"] = "console"

    
    
    
    SCHEDULER_ENABLED: bool = True
    SCHEDULER_INTERVAL_MINUTES: int = 15
    NOTIFICATION_MAX_ATTEMPTS: int = 5
    NOTIFICATION_RETRY_BASE_SECONDS: int = 60
    NOTIFICATION_BATCH_SIZE: int = 50

    
    
    
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    @field_validator("SECRET_KEY")
    @classmethod
    def _warn_weak_secret(cls, value: str) -> str:
        if "CHANGE_ME" in value:
            
            pass
        return value

    @model_validator(mode="after")
    def _enforce_production_safety(self) -> "Settings":
        
        if self.ENVIRONMENT != "production":
            return self
        if "CHANGE_ME" in self.SECRET_KEY or len(self.SECRET_KEY) < 32:
            raise ValueError(
                "SECRET_KEY must be a strong, unique value of at least 32 characters "
                "when ENVIRONMENT=production."
            )
        if not self.COOKIE_SECURE:
            raise ValueError("COOKIE_SECURE must be true in production (HTTPS only).")
        if self.EMAIL_BACKEND != "smtp":
            raise ValueError("EMAIL_BACKEND must be 'smtp' in production.")
        if not self.SMTP_HOST or not self.SMTP_FROM:
            raise ValueError("SMTP_HOST and SMTP_FROM must be configured in production.")
        if "cors" in self.FRONTEND_ORIGINS.lower() and "*" in self.FRONTEND_ORIGINS:
            raise ValueError("Wildcard CORS origins are not allowed in production.")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]

    @property
    def sync_database_url(self) -> str:
        
        url = self.DATABASE_URL
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+pymysql://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg2://", 1)
        return url

    @property
    def database_is_sqlite(self) -> bool:
        return self.sync_database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
