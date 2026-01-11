import logging
import mlflow

from api.src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _create_offline_markdown(original_text: str, plot_filenames: list[str]) -> str:
    """
    Internal Helper: Converts API URLs to relative local paths
    specifically for the archived Markdown report.

    It iterates ONLY through the actual generated files to ensure
    we don't break links or rewrite hallucinatory paths.
    """
    offline_text = original_text

    for filename in plot_filenames:
        api_path = f"/api/v1/plots/{filename}"
        local_path = f"plots/{filename}"

        offline_text = offline_text.replace(api_path, local_path)

    return offline_text


def upload_run_artifacts(response_text: str, generated_plots: list[str]):
    """
    Handles the governance aspect: uploads the plots and the modified
    report.md to the current MLflow/MinIO run.

    This function is Fail-Safe: it catches its own exceptions to avoid
    breaking the main API response if the artifact server is down.
    """
    if not settings.MLFLOW_ENABLE:
        return

    try:
        run = mlflow.last_active_run()

        if not run:
            logger.warning("No active MLflow run found. Skipping artifact upload.")
            return

        run_id = run.info.run_id
        logger.info(f"Packaging artifacts for Run ID: {run_id}")

        for filename in generated_plots:
            file_path = settings.PLOTS_DIR / filename

            if file_path.exists():
                mlflow.log_artifact(local_path=str(file_path), artifact_path="plots")
                logger.debug(f"   -> Uploaded: {filename}")
            else:
                logger.warning(f"   -> File missing on disk: {filename}")

        report_offline = _create_offline_markdown(response_text, generated_plots)
        mlflow.log_text(report_offline, "report.md")

        logger.info("Artifact Package (Report + Plots) uploaded successfully.")

    except Exception as e:
        logger.error(f"Governance upload failed: {e}", exc_info=True)
