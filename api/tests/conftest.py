import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.src.config import get_settings


@pytest.fixture
def client():
    """
    Creates a TestClient instance.
    We override the dependency to ensure tests run against the current app state.
    """
    return TestClient(app)


@pytest.fixture
def mock_settings(monkeypatch):
    """
    Optional: Override settings for testing (e.g., disable MLflow).
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "MLFLOW_ENABLE", False)
    return settings
