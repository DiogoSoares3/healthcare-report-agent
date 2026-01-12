import logging
import mlflow
from api.src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def setup_telemetry():
    """
    Configures the global telemetry and experiment tracking settings.

    This function initializes the connection to the MLflow server and enables

    **PydanticAI Autologging**. This feature automatically captures:

    - LLM Prompts and Completions.
    - Tool calls and outputs.
    - Token usage and latency.

    **Configuration:**

    - Reads `MLFLOW_TRACKING_URI` from settings.
    - Sets the active experiment to `MLFLOW_EXPERIMENT_NAME`.
    - Enables `log_traces=True` for detailed trace views.
    """
    if not settings.MLFLOW_ENABLE:
        logger.info("Telemetry (MLflow) is disabled via config.")
        return

    logger.info(f"Setting up MLflow tracking at {settings.MLFLOW_TRACKING_URI}...")

    try:
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)

        mlflow.pydantic_ai.autolog(log_traces=True)

        logger.info("MLflow Autolog enabled successfully.")

    except Exception as e:
        logger.error(f"Failed to initialize MLflow: {e}", exc_info=True)


def set_trace_tags(tags: dict):
    """
    Attaches metadata tags to the current active MLflow run/trace.

    This allows for better filtering and organization of traces in the MLflow UI
    (e.g., filtering all reports focused on 'pediatrics').

    Args:
        tags (dict): A dictionary of key-value pairs (e.g., `{'focus': 'ICU'}`).
    """
    if not settings.MLFLOW_ENABLE:
        return

    try:
        active_run = mlflow.active_run()

        if active_run:
            mlflow.set_tags(tags)

    except Exception as e:
        logger.warning(f"Could not set trace tags: {e}")
