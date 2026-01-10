import logging
from functools import lru_cache

from fastapi import Depends
from pydantic_ai import Agent
from pydantic_ai.settings import ModelSettings
from pydantic_ai_guardrails import GuardedAgent
from pydantic_ai_guardrails.guardrails.input import (
    length_limit,
    pii_detector,
    prompt_injection,
    toxicity,
)
from pydantic_ai_guardrails.guardrails.output import (
    validate_tool_parameters,
)

from api.src.config import get_settings, Settings
from api.src.db.connection import get_schema_info
from api.src.agents.deps import AgentDeps
from api.src.agents.prompts import build_system_prompt

from api.src.tools.stats import create_stats_tool, validate_sql_safety
from api.src.tools.plot import create_plot_tool
from api.src.tools.search import create_search_tool
from api.src.tools.schemas import StatsParams, SearchParams, PlotParams

logger = logging.getLogger(__name__)


class SRAGAgentOrchestrator:
    """
    Orchestrates the lifecycle of the SRAG Reporting Agent.
    Implements the Singleton pattern via lru_cache for efficiency.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        logger.info("Initializing SRAG Agent Orchestrator...")

        try:
            self.schema_info = get_schema_info()
            logger.debug("Database schema loaded successfully.")
        except Exception as e:
            logger.warning(f"Could not load schema on init (ETL might be running): {e}")
            self.schema_info = "Schema not available yet."

        self.base_agent = Agent(
            model=self.settings.OPENAI_MODEL,
            system_prompt=build_system_prompt(self.schema_info),
            deps_type=AgentDeps,
            tools=[
                create_stats_tool(),
                create_search_tool(api_key=settings.TAVILY_API_KEY.get_secret_value()),
                create_plot_tool(output_dir=settings.PLOTS_DIR),
            ],
            model_settings=ModelSettings(
                temperature=self.settings.TEMPERATURE,
                max_tokens=self.settings.MAX_OUTPUT_TOKENS,
            ),
        )

        self.agent = GuardedAgent(
            self.base_agent,
            input_guardrails=[
                length_limit(max_tokens=self.settings.MAX_INPUT_TOKENS),
                pii_detector(),
                prompt_injection(),
                toxicity(),
            ],
            output_guardrails=[
                # secret_redaction(),
                validate_tool_parameters(
                    schemas={
                        "stats_tool": StatsParams,
                        "plot_tool": PlotParams,
                        "tavily_search": SearchParams,
                    },
                    validators={"stats_tool": validate_sql_safety},
                    allow_undefined_tools=False,
                ),
            ],
        )
        logger.info("SRAG Agent initialized with Guardrails.")

    async def run(self, query: str) -> str:
        logger.info(f"Agent received query: {query}")

        deps = AgentDeps(
            db_path=str(self.settings.DB_PATH),
        )

        try:
            result = await self.agent.run(query, deps=deps)

            logger.info(f"Run completed. Usage: {result.usage()}")

            return result.data

        except Exception as e:
            logger.error(f"Agent execution failed: {e}", exc_info=True)
            return f"I encountered an error while processing your request: {str(e)}"


@lru_cache
def get_orchestrator(
    settings: Settings = Depends(get_settings),
) -> SRAGAgentOrchestrator:
    return SRAGAgentOrchestrator(settings)
