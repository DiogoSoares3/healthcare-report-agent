import logging
from dataclasses import dataclass

from pydantic_ai import RunContext
from pydantic_ai.tools import Tool

from api.src.agents.deps import AgentDeps

logger = logging.getLogger(__name__)


@dataclass
class StatsTool:
    """
    Tool responsible for executing analytical queries against the DuckDB database.
    """

    def __call__(self, ctx: RunContext[AgentDeps], sql_query: str) -> str:
        """
        Executes a SQL query against the 'srag_analytics' table.

        Args:
            ctx: Runtime context containing the DB connection.
            sql_query: The executable SQL query.
        """
        logger.info(f"Received SQL: {sql_query}")

        # Using agent's dependency
        con = ctx.deps.get_db_connection(read_only=True)

        try:
            df = con.execute(sql_query).df()

            if len(df) > 20:
                return (
                    f"Error: Result contains {len(df)} rows. "
                    "Please aggregate your query using GROUP BY or use LIMIT 20."
                )

            if df.empty:
                return "Result: No data found for this query."

            return df.to_markdown(index=False)

        except Exception as e:
            logger.error(f"SQL Execution failed: {e}")
            return f"SQL Error: {str(e)}"
        finally:
            con.close()


def create_stats_tool() -> Tool[AgentDeps]:
    """Factory to create the Stats Tool."""
    return Tool(
        StatsTool().__call__,
        name="stats_tool",
        description=(
            "Executes a SQL query against the 'srag_analytics' table and returns the results. "
            "Use this to calculate metrics like mortality, counts, and averages."
        ),
    )


def validate_sql_safety(args: dict) -> str | None:
    """
    Security Validator: Checks for destructive SQL commands.
    Used by the 'validate_tool_parameters' guardrail.
    """
    query = args.get("sql_query", "").upper()
    forbidden_keywords = ["DROP", "DELETE", "TRUNCATE", "ALTER", "UPDATE", "INSERT"]

    if any(keyword in query for keyword in forbidden_keywords):
        return f"Security Violation: Destructive SQL commands ({', '.join(forbidden_keywords)}) are strictly prohibited."

    return None
