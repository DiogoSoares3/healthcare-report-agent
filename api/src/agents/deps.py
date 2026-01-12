from dataclasses import dataclass

import duckdb
from duckdb import DuckDBPyConnection


@dataclass
class AgentDeps:
    """
    Dependency Injection container for PydanticAI Agents.

    This class encapsulates external resources (specifically the database path)
    that need to be passed into the Agent's runtime context. It allows the Agent
    to establish connections dynamically during execution.

    Attributes:
        db_path (str): The filesystem path to the DuckDB database file.
    """

    db_path: str

    def get_db_connection(self, read_only: bool = True) -> DuckDBPyConnection:
        """
        Creates a new connection to the DuckDB database.

        Args:
            read_only (bool): Safety flag to prevent accidental writes. Defaults to `True`.

        Returns:
            DuckDBPyConnection: An active database connection object.
        """
        return duckdb.connect(self.db_path, read_only=read_only)
