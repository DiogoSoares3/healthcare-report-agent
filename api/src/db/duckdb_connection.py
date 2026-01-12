import logging

import duckdb
from duckdb import DuckDBPyConnection

from api.src.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

COLUMN_METADATA = {
    "DT_NOTIFIC": "Notification Date. The primary timestamp for all temporal analysis (trends, seasonality).",
    "age": "Patient Age (Years). Numeric value.",
    "sex": "Biological Sex. Categories: M (Male), F (Female), I (Ignored).",
    "outcome_lbl": "Case Outcome (Evolution). Indicates if patient recovered or died. CRITICAL for Mortality Rate.",
    "icu_lbl": "ICU Admission Status (Yes/No). Indicates severity and resource usage.",
    "diagnosis_lbl": "Final Diagnosis Classification. E.g., Influenza, Covid-19. Use this to differentiate outbreaks.",
    "vaccine_lbl": "Influenza (Flu) Vaccination Status. Indicates if patient took the flu vaccine in the last campaign.",
    "vaccine_cov_lbl": "COVID-19 Vaccination Status. Indicates if patient took the covid vaccine.",
    "cardiopati_1": "Comorbidity: Heart Disease. (1 = Yes, 0 = No).",
    "diabetes_1": "Comorbidity: Diabetes. (1 = Yes, 0 = No).",
    "obesidade_1": "Comorbidity: Obesity. (1 = Yes, 0 = No).",
}


def get_db_connection(read_only: bool = True) -> DuckDBPyConnection:
    """
    Establishes a connection to the local DuckDB database.

    Args:
        read_only (bool): If True, opens the database in read-only mode to prevent
            accidental writes during analysis. Defaults to `True`.

    Returns:
        DuckDBPyConnection: The active database connection object.

    Raises:
        FileNotFoundError: If the database file (`srag_analytics.db`) does not exist
            at the configured path (usually indicating the ETL pipeline hasn't run).
    """
    if not settings.DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {settings.DB_PATH}. Run ETL pipeline first."
        )

    con = duckdb.connect(str(settings.DB_PATH), read_only=read_only)
    return con


def get_schema_info() -> str:
    """
    Generates a rich, LLM-friendly textual representation of the database schema.

    This function combines static metadata descriptions with dynamic data profiling
    to help the AI Agent understand the dataset's structure and content.

    **Process:**

    1.  **Reflect Schema:** Queries DuckDB to get column names and types.
    2.  **Match Metadata:** Aligns columns with the `COLUMN_METADATA` dictionary.
    3.  **Data Profiling (Dynamic):** For categorical columns (VARCHAR), it executes
        a `GROUP BY` query to fetch the top 5 most frequent values. This allows the
        Agent to see actual examples (e.g., seeing 'Covid-19' vs 'SARS-CoV-2').
    4.  **Formatting:** Compiles everything into a Markdown list string.

    Returns:
        str: A formatted string describing columns, types, descriptions, and sample values.
             Returns an error message string if the schema cannot be read.
    """
    con = get_db_connection()
    try:
        try:
            df_schema = con.execute("DESCRIBE srag_analytics").df()
        except Exception as e:
            return f"Error reading schema table: {e}"

        schema_lines = []
        schema_lines.append("Table: srag_analytics")
        schema_lines.append("=" * 30)

        for col_name, description in COLUMN_METADATA.items():
            schema_row = df_schema[df_schema["column_name"] == col_name]

            if schema_row.empty:
                logger.warning(
                    f"Column '{col_name}' defined in metadata but not found in DB table."
                )
                continue

            col_type = schema_row.iloc[0]["column_type"]

            values_str = ""
            if "VARCHAR" in col_type.upper():
                try:
                    query = f"""
                        SELECT {col_name}, COUNT(*) as freq
                        FROM srag_analytics
                        WHERE {col_name} IS NOT NULL
                        GROUP BY {col_name}
                        ORDER BY freq DESC
                        LIMIT 5
                    """
                    df_distinct = con.execute(query).df()

                    vals = [f"'{v}'" for v in df_distinct[col_name].tolist()]
                    values_str = f" | Sample Values: [{', '.join(vals)}]"
                except Exception:
                    pass

            line = f"- **{col_name}** ({col_type}) | Description: {description}{values_str}"
            schema_lines.append(line)

        return "\n".join(schema_lines)

    except Exception as e:
        logger.error(f"Failed to generate schema info: {e}")
        return "Error: Could not retrieve database schema."
    finally:
        con.close()
