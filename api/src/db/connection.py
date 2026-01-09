import duckdb
from duckdb import DuckDBPyConnection
from api.src.config import settings


def get_db_connection(read_only: bool = True) ->  DuckDBPyConnection:
    if not settings.DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {settings.DB_PATH}. Run ETL pipeline first.")
    
    con = duckdb.connect(str(settings.DB_PATH), read_only=read_only)
    return con

def execute_query(query: str, params: tuple = None) -> list:
    con = get_db_connection()
    try:
        if params:
            return con.execute(query, params).fetchall()
        return con.execute(query).fetchall()
    finally:
        con.close()

def get_schema_info() -> str:
    con = get_db_connection()
    try:
        df = con.execute("DESCRIBE srag_analytics").df()
        return df.to_markdown(index=False)
    finally:
        con.close()
