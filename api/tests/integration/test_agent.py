import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from typing import Any

from pydantic_ai.models import Model
from pydantic_ai.messages import ModelResponse, ToolCallPart, TextPart
from pydantic_ai.settings import ModelSettings
from pydantic_ai_guardrails.exceptions import OutputGuardrailViolation

from api.main import app
from api.src.agents.orchestrator import SRAGAgentOrchestrator, get_orchestrator
from api.src.config import get_settings
from api.src.agents.deps import AgentDeps


class FixedResponseModel(Model):
    def __init__(self, response_parts: list[Any]):
        self.response_parts = response_parts
        self._call_count = 0

    async def request(
        self,
        messages: list[Any],
        model_settings: ModelSettings | None,
        model_request_parameters: Any | None,
    ) -> ModelResponse:
        if self._call_count == 0:
            self._call_count += 1
            return ModelResponse(parts=self.response_parts)
        else:
            return ModelResponse(parts=[TextPart("Testing complete.")])

    @property
    def model_name(self) -> str:
        return "fixed-response-mock"

    @property
    def system(self) -> str | None:
        return "mock-system-prompt"


@pytest.fixture
def mock_deps():
    deps = MagicMock(spec=AgentDeps)
    deps.db_path = ":memory:"

    mock_conn = MagicMock()
    mock_conn.execute.return_value.df.return_value.empty = False

    deps.get_db_connection.return_value = mock_conn
    return deps


@pytest.fixture
def orchestrator():
    """Initializes the Orchestrator with Test settings."""
    settings = get_settings()
    return SRAGAgentOrchestrator(settings)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
async def test_agent_sql_guardrail_interception(orchestrator, mock_deps):
    malicious_response = [
        ToolCallPart(
            tool_name="stats_tool",
            args={"sql_query": "DROP TABLE srag_analytics; --"},
            tool_call_id="call_rogue_1",
        )
    ]

    orchestrator.base_agent.model = FixedResponseModel(malicious_response)

    with pytest.raises(OutputGuardrailViolation) as excinfo:
        await orchestrator.agent.run("Please count the records", deps=mock_deps)

    error_msg = str(excinfo.value)
    assert "validate_tool_parameters" in error_msg
    assert "Security Violation" in error_msg
    assert "DROP" in error_msg


@pytest.mark.asyncio
async def test_agent_tool_routing_success(orchestrator, mock_deps):
    valid_response = [
        ToolCallPart(
            tool_name="stats_tool",
            args={"sql_query": "SELECT count(*) FROM srag"},
            tool_call_id="call_valid_1",
        )
    ]

    orchestrator.base_agent.model = FixedResponseModel(valid_response)

    await orchestrator.agent.run("Count cases", deps=mock_deps)

    mock_conn = mock_deps.get_db_connection.return_value
    mock_conn.execute.assert_called()

    called_query = mock_conn.execute.call_args[0][0]
    assert "SELECT count(*)" in called_query


def test_full_report_flow_integration(client):
    mock_orchestrator = MagicMock()

    mock_result = MagicMock()
    mock_result.output = "Report generated with **bold text**."
    mock_result.all_messages.return_value = []

    mock_orchestrator.run = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator

    try:
        payload = {"focus_area": "Children under 5"}
        response = client.post("/api/v1/agent/report", json=payload)

        assert response.status_code == 200, f"API failed: {response.text}"

        data = response.json()
        assert data["response"] == "Report generated with **bold text**."
        assert "execution_time" in data

        called_prompt = mock_orchestrator.run.call_args[0][0]
        assert "Children under 5" in called_prompt
        assert "STRICTLY FOLLOW" in called_prompt

    finally:
        app.dependency_overrides = {}
