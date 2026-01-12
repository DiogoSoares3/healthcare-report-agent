from typing import Any

from pydantic_ai.tools import Tool
from pydantic_ai.common_tools.tavily import tavily_search_tool


def create_search_tool(api_key: str) -> Tool[Any]:
    """
    Factory to create the Tavily Web Search Tool.

    This tool enables the agent to fetch real-time news and context from the web
    to enrich the data analysis (e.g., explaining why cases rose in a specific month
    by finding news about a new variant).

    Args:
        api_key (str): The Tavily API Key.

    Returns:
        Tool: A configured PydanticAI tool for web search.
    """
    return tavily_search_tool(api_key=api_key)
