from dataclasses import dataclass

import duckdb
from duckdb import DuckDBPyConnection


@dataclass
class AgentDeps:
    db_path: str

    def get_db_connection(self, read_only: bool = True) -> DuckDBPyConnection:
        return duckdb.connect(self.db_path, read_only=read_only)
