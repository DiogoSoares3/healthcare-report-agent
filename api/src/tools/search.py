from typing import Any

from pydantic_ai.tools import Tool
from pydantic_ai.common_tools.tavily import tavily_search_tool


def create_search_tool(api_key: str) -> Tool[Any]:
    """
    Factory to create the Tavily Search Tool.
    """
    return tavily_search_tool(api_key=api_key)
