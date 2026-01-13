from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    """
    Application configuration and environment variables.

    This class defines the global settings for the API, including file paths,
    external API keys, and model parameters. Values are loaded from a `.env` file
    or system environment variables.

    Attributes:
        API_TITLE (str): Title used in the OpenAPI documentation.
        API_VERSION (str): Current API version.
        DATA_URL (str): Source URL for the raw SRAG CSV data.
        FORCE_UPDATE (bool): If True, forces re-download of data even if cached.
        RAW_DATA_PATH (Path): Local path to store the raw CSV.
        DB_PATH (Path): Local path for the processed SQLite database.
        PLOTS_DIR (Path): Directory where generated charts are saved.
        OPENAI_API_KEY (SecretStr): Key for OpenAI API access.
        TAVILY_API_KEY (SecretStr): Key for Tavily Search API access.
        OPENAI_MODEL (str): The specific LLM model identifier (e.g., 'openai:gpt-4.1-mini').
        TEMPERATURE (float): Determinism setting for the LLM (0.0 for maximum determinism).
        MLFLOW_TRACKING_URI (str): URI for the MLflow tracking server.
        MLFLOW_ENABLE (bool): Master switch to enable/disable MLflow logging.
    """

    API_TITLE: str = "SRAG Reporting Agent"
    API_VERSION: str = "1.0.0"

    DATA_URL: str = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br/SRAG/2025/INFLUD25-22-12-2025.csv"
    FORCE_UPDATE: bool = False

    RAW_DATA_PATH: Path = PROJECT_DIR / "data" / "raw" / "data.csv"
    DB_PATH: Path = PROJECT_DIR / "data" / "processed" / "srag_analytics.db"
    PLOTS_DIR: Path = PROJECT_DIR / "data" / "plots"

    OPENAI_API_KEY: SecretStr
    TAVILY_API_KEY: SecretStr
    OPENAI_MODEL: str = "openai:gpt-4.1-mini"

    TEMPERATURE: float = 0.0
    MAX_INPUT_TOKENS: int = 1000
    MAX_OUTPUT_TOKENS: int = 2000

    MLFLOW_TRACKING_URI: str = "http://mlflow:5000"
    MLFLOW_EXPERIMENT_NAME: str = "SRAG"
    MLFLOW_ENABLE: bool = True

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", frozen=True
    )


@lru_cache
def get_settings() -> Settings:
    """
    Retrieves the cached application settings.

    Uses `functools.lru_cache` to ensure the settings are loaded from the environment
    only once per process, improving performance.

    Returns:
        Settings: The singleton instance of the application configuration.
    """
    return Settings()
