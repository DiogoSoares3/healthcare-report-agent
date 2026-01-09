from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    API_TITLE: str = "SRAG Reporting Agent"
    API_VERSION: str = "1.0.0"
    
    DATA_URL: str = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-22-12-2025.csv"
    FORCE_UPDATE: bool = False
    
    RAW_DATA_PATH: Path = PROJECT_DIR / "data" / "raw" / "data.csv"
    DB_PATH: Path = PROJECT_DIR / "data" / "processed" / "srag_analytics.db"
    
    OPENAI_API_KEY: str
    # TAVILY_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    return Settings()
