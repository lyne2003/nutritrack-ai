# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Pydantic v2 settings config
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "NutriTrack AI Backend"
    ENV: str = "dev"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    YOLO_MODEL_PATH: str | None = None

    FATSECRET_CLIENT_ID: str = ""
    FATSECRET_CLIENT_SECRET: str = ""
    FATSECRET_TOKEN_URL: str = "https://oauth.fatsecret.com/connect/token"
    FATSECRET_API_BASE: str = "https://platform.fatsecret.com/rest"



settings = Settings()
