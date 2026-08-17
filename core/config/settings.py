from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
ROOT_DIR = Path(__file__).resolve().parents[2]
class Settings(BaseSettings):
    app_name: str = "JARVIS OS"
    environment: str = "development"
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "INFO"
    database_path: str = "database/jarvis.db"
    api_url: str = "http://127.0.0.1:8765"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", env_prefix="JARVIS_", case_sensitive=False, extra="ignore")
settings = Settings()
