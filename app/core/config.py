from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Application settings
    APP_ENV: str = Field(default="development")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8082)

    # CORS origins as comma-separated string
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173,http://localhost:8081,http://localhost:8082"
    )

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/aturmodal"
    )

    # Redis (Rate Limiting)
    REDIS_URL: str = Field(default="redis://localhost:6379")

    # Security
    JWT_SECRET_KEY: str = Field(
        default="GANTI_INI_DI_PRODUCTION_DENGAN_STRING_RANDOM_64_KARAKTER"
    )
    JWT_ALGORITHM: str = Field(default="HS256")
    JWT_EXPIRE_MINUTES: int = Field(default=1440)  # 24 hours

    # Google Gemini API
    GEMINI_API_KEY: str = Field(default="")
    GEMINI_TIMEOUT_SECONDS: float = Field(default=30.0)

    @property
    def allowed_origins_list(self) -> List[str]:
        return [
            origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()
        ]


settings = Settings()
