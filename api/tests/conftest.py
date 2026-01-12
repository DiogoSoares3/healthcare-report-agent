import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.src.config import get_settings


@pytest.fixture
def client():
    """
    Creates a `TestClient` instance bound to the FastAPI app.

    This fixture ensures that a fresh client is available for each test function,
    allowing for isolated HTTP request testing against the application endpoints.

    Returns:
        TestClient: The HTTP client for making requests to the app.
    """
    return TestClient(app)


@pytest.fixture
def mock_settings(monkeypatch):
    """
    Overrides application settings for the testing environment.

    **Adjustments:**

    * **MLFLOW_ENABLE = False:** Disables telemetry to prevent test runs from
        polluting the production MLflow server with noise data.

    Args:
        monkeypatch: Pytest's fixture for safely modifying attributes/env vars.

    Returns:
        Settings: The modified settings object.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "MLFLOW_ENABLE", False)
    return settings
