import re

from pydantic_ai import AgentRunResult
from pydantic_ai.messages import ToolReturnPart


def extract_plots_from_result(result: AgentRunResult) -> list[str]:
    """
    Scans the agent's execution trace to find generated plot filenames
    from 'plot_tool' tool returns.

    - Handles absolute paths (e.g., /app/data/plots/file.png)
    - Handles relative paths (e.g., data/plots/file.png)
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
    offline_text = original_text

    offline_text = re.sub(
        r"\((?:https?://[^)]+)?/api/v1/plots/([^)]+\.png)\)",
        r"(plots/\1)",
        offline_text,
    )

    return offline_text
