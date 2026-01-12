import logging
import time

import mlflow
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from api.src.config import get_settings


logger = logging.getLogger("api.middleware")
settings = get_settings()


class MLflowTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic MLflow experiment tracking per request.

    This middleware intercepts HTTP requests to wrap them within an MLflow Run context,
    ensuring full observability of API usage, performance, and errors.

    **Logic Flow:**

    1.  **Filter:** Skips tracking for health checks and documentation endpoints.
    2.  **Start Run:** Initiates a new MLflow run (nested) named after the method and path.
    3.  **Tagging:** Logs request metadata (Method, URL) as MLflow tags.
    4.  **Execution:** Awaits the request processing.
    5.  **Status Update:**
        - If status code >= 500, marks the run as `FAILED`.
        - If successful, marks as `FINISHED`.
    6.  **Exception Handling:** Captures unhandled exceptions, logs the error type
        and details to MLflow, and re-raises the exception to FastAPI.

    Attributes:
        app (ASGIApp): The ASGI application instance.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.MLFLOW_ENABLE or request.url.path in [
            "/health",
            "/docs",
            "/openapi.json",
        ]:
            return await call_next(request)

        run_name = f"{request.method}_{request.url.path}_{int(time.time())}"
        active_run_context = mlflow.start_run(run_name=run_name, nested=True)

        try:
            mlflow.set_tag("http.method", request.method)
            mlflow.set_tag("http.url", str(request.url))

            with active_run_context:
                response = await call_next(request)

            if response.status_code >= 500:
                mlflow.set_tag("status", "FAILED")
                mlflow.end_run(status="FAILED")
            else:
                mlflow.end_run(status="FINISHED")

            return response

        except Exception as e:
            logger.error(f"Request failed: {e}")
            mlflow.log_param("error_type", type(e).__name__)
            mlflow.log_text(str(e), "error_details.txt")
            mlflow.end_run(status="FAILED")
            raise e
