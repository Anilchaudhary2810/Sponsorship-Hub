from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
import json

class Settings(BaseSettings):
    # Base Config
    APP_NAME: str = "Sponsorship Management"
    DEBUG: bool = False
    ENV: str = "development"
    
    # Security
    SECRET_KEY: str = "placeholder_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = "sqlite:///./sponsorship.db"
    REDIS_URL: Optional[str] = None
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE_SECONDS: int = 1800
    MAX_REQUEST_BODY_BYTES: int = 2_000_000
    
    # Razorpay
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    
    # SMTP / Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SMTP_FROM: str = "noreply@sponsorship.com"
    

    # CORS — must list explicit origins when allow_credentials=True (wildcard is invalid)
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "https://sponsorship-hub.vercel.app"]
    
    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        if isinstance(v, str):
            parsed = json.loads(v)
            if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
                return parsed
            raise ValueError("CORS_ORIGINS JSON value must be a list of strings")
        if isinstance(v, list):
            return v
        raise ValueError(v)

    @model_validator(mode="after")
    def validate_security_settings(self):
        env_value = (self.ENV or "").lower()
        is_production = env_value in {"production", "prod"}

        if is_production and self.SECRET_KEY == "placeholder_change_in_production":
            raise ValueError("SECRET_KEY must be set to a strong value in production.")

        if is_production and not self.RAZORPAY_WEBHOOK_SECRET:
            raise ValueError("RAZORPAY_WEBHOOK_SECRET must be configured in production.")

        return self
    
    model_config = SettingsConfigDict(
        env_file=(".env", "backend/.env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
