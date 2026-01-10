import logging
import mlflow
from api.src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def setup_telemetry():
    """
    Initializes MLflow instrumentation for PydanticAI.
    Should be called at application startup.
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
    Helper to add metadata tags to the current active trace/run.
    Useful for filtering traces by endpoint or user focus area.
    """
    if not settings.MLFLOW_ENABLE:
        return

    try:
        active_run = mlflow.active_run()

        if active_run:
            mlflow.set_tags(tags)

    except Exception as e:
        logger.warning(f"Could not set trace tags: {e}")
