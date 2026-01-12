import os
import logging

import requests
import pandas as pd
import duckdb

from api.src.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()


def download_data():
    """
    Downloads the SRAG data CSV from the official source if not present locally.

    This function implements a streaming download to handle large files efficiently
    without consuming excessive memory.

    **Checks:**

    - If `RAW_DATA_PATH` exists and `FORCE_UPDATE` is false, the download is skipped.
    - Creates parent directories if they don't exist.

    Raises:
        requests.exceptions.HTTPError: If the remote server returns an error code (4xx/5xx).
        IOError: If writing to the local disk fails.
    """
    if (
        settings.RAW_DATA_PATH.exists()
        and os.getenv("FORCE_UPDATE", "false").lower() != "true"
    ):
        logger.info(
            f"Raw file already exists at {settings.RAW_DATA_PATH}. Skipping download."
        )
        return

    logger.info(f"Starting download from {settings.DATA_URL}...")
    try:
        response = requests.get(settings.DATA_URL, stream=True)
        response.raise_for_status()

        settings.RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(settings.RAW_DATA_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("Download completed successfully.")
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise


def process_and_load():
    """
    Processes the raw CSV data and loads it into a DuckDB database.

    This function performs the 'Transform' and 'Load' steps of the ETL pipeline:

    1.  **Read:** Loads specific columns from the raw CSV using Pandas.
    2.  **Clean:**
        - Converts dates and handles parsing errors.
        - Maps categorical codes (e.g., 1, 2) to human-readable labels (e.g., 'Cure', 'Death').
        - Normalizes binary fields (vaccination, comorbidities).
    3.  **Load:** Persists the processed DataFrame into a DuckDB table (`srag_analytics`).

    **Column Mappings Applied:**

    - `outcome_lbl`: 1 -> Cure, 2 -> Death_SRAG, 3 -> Death_Other.
    - `diagnosis_lbl`: 1 -> Influenza, 5 -> Covid-19.
    - `icu_lbl`, `vaccine_*`: 1 -> Yes, 2 -> No.

    Raises:
        Exception: If data processing fails (e.g., memory issues, schema mismatch).
    """
    logger.info("Starting data processing...")

    selected_cols = [
        "DT_NOTIFIC",
        "EVOLUCAO",
        "UTI",
        "VACINA",
        "VACINA_COV",
        "CLASSI_FIN",
        "NU_IDADE_N",
        "CS_SEXO",
        "CARDIOPATI",
        "DIABETES",
        "OBESIDADE",
    ]

    try:
        df = pd.read_csv(
            settings.RAW_DATA_PATH,
            sep=";",
            encoding="utf-8",
            usecols=selected_cols,
            low_memory=False,
        )
        logger.info(f"Raw data loaded. Total records: {len(df)}")

        df["DT_NOTIFIC"] = pd.to_datetime(df["DT_NOTIFIC"], errors="coerce")
        df = df.dropna(subset=["DT_NOTIFIC"])

        def clean_categorical(series, mapping):
            return (
                pd.to_numeric(series, errors="coerce")
                .fillna(0)
                .astype(int)
                .map(mapping)
                .fillna("Ignored")
            )

        map_outcome = {1: "Cure", 2: "Death_SRAG", 3: "Death_Other"}
        map_binary = {1: "Yes", 2: "No"}
        map_diagnosis = {1: "Influenza", 5: "Covid-19"}

        df["outcome_lbl"] = clean_categorical(df["EVOLUCAO"], map_outcome)
        df["icu_lbl"] = clean_categorical(df["UTI"], map_binary)
        df["vaccine_lbl"] = clean_categorical(df["VACINA"], map_binary)
        df["vaccine_cov_lbl"] = clean_categorical(df["VACINA_COV"], map_binary)
        df["diagnosis_lbl"] = clean_categorical(df["CLASSI_FIN"], map_diagnosis)

        df["age"] = pd.to_numeric(df["NU_IDADE_N"], errors="coerce").clip(0, 120)
        df["sex"] = df["CS_SEXO"].fillna("Ignored")

        for col in ["CARDIOPATI", "DIABETES", "OBESIDADE"]:
            df[col.lower()] = pd.to_numeric(df[col], errors="coerce").apply(
                lambda x: 1 if x == 1 else 0
            )

        logger.info(f"Saving processed data to {settings.DB_PATH}...")
        settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)

        con = duckdb.connect(str(settings.DB_PATH))
        con.execute("CREATE OR REPLACE TABLE srag_analytics AS SELECT * FROM df")

        count = con.execute("SELECT COUNT(*) FROM srag_analytics").fetchone()[0]

        logger.info(f"ETL completed. Total records in DuckDB: {count}")

        con.close()

    except Exception as e:
        logger.error(f"Processing error: {e}")
        raise


def run_pipeline():
    """
    Orchestrates the full ETL (Extract, Transform, Load) pipeline.

    This is the main entry point for data ingestion. It ensures that the application
    has a valid local database to work with. It respects caching mechanisms to avoid
    redundant work on restart.

    **Logic:**

    1.  Checks if the database (`DB_PATH`) already exists.
    2.  If it exists and `FORCE_UPDATE` is False, it skips execution (Idempotency).
    3.  Otherwise, triggers `download_data()` followed by `process_and_load()`.
    """
    if settings.DB_PATH.exists() and not settings.FORCE_UPDATE:
        logger.info(
            "DuckDB database already exists and FORCE_UPDATE=false. Using cached data."
        )
        return

    download_data()
    process_and_load()


if __name__ == "__main__":
    run_pipeline()
