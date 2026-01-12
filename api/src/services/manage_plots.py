import re

from pydantic_ai import AgentRunResult
from pydantic_ai.messages import ToolReturnPart


def extract_plots_from_result(result: AgentRunResult) -> list[str]:
    """
    Parses the Agent's execution trace to identify generated plot files.

    Since the LLM calls a plotting tool, the filename is returned within a
    `ToolReturnPart` message. This function scans the history to extract these
    filenames reliably, rather than relying on the LLM's final text description.

    Args:
        result (AgentRunResult): The result object returned by `agent.run()`.

    Returns:
        list[str]: A list of unique filenames (e.g., `['trend_30d.png']`) found
        in the tool execution outputs.
    """
    plot_files = []

    messages = result.all_messages()

    for msg in messages:
        if hasattr(msg, "parts"):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name == "plot_tool":
                    content = str(part.content)

                    match = re.search(
                        r"data/plots/([^/\s]+\.png)", content, re.IGNORECASE
                    )

                    if match:
                        filename = match.group(1)
                        plot_files.append(filename)

    return list(set(plot_files))


def create_offline_markdown(original_text: str, plot_filenames: list[str]) -> str:
    """
    Rewrites image links in the Markdown report for offline portability.

    The live API serves images via endpoints (e.g., `/api/v1/plots/...`).
    However, when saving the report to MLflow or zip files, these links need
    to be relative filesystem paths (e.g., `plots/...`) to render correctly
    without a running server.

    Args:
        original_text (str): The Markdown text with API URLs.
        plot_filenames (list[str]): List of valid plot filenames to verify/replace.

    Returns:
        str: The Markdown text with updated image paths.
    """
    offline_text = original_text

    offline_text = re.sub(
        r"\((?:https?://[^)]+)?/api/v1/plots/([^)]+\.png)\)",
        r"(plots/\1)",
        offline_text,
    )

    return offline_text
