from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.src.middleware.observability import MLflowTrackingMiddleware
from api.src.services.ingest import run_pipeline
from api.src.routers import agent
from api.src.config import get_settings
from api.src.services.telemetry import setup_telemetry

logger = logging.getLogger("api")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    setup_telemetry()

    logger.info("Checking data integrity (ETL)...")
    try:
        run_pipeline()
        logger.info("Data is ready for use.")
    except Exception as e:
        logger.critical(f"Critical failure during data initialization: {e}")

    yield

    logger.info("Shutting down API...")


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    lifespan=lifespan,
    docs_url="/api/v1/docs",
)

app.add_middleware(MLflowTrackingMiddleware)

### For Frontend access to plots
app.mount("/api/v1/plots", StaticFiles(directory=settings.PLOTS_DIR), name="plots")

app.include_router(agent.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "db_ready": settings.DB_PATH.exists()}
