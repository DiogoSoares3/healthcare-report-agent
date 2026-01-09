from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from api.src.services.ingest import run_pipeline

logger = logging.getLogger("api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Checking data integrity (ETL)...")
    try:
        run_pipeline()
        logger.info("Data is ready for use.")
    except Exception as e:
        logger.critical(f"Critical failure during data initialization: {e}")
    
    yield
    
    logger.info("Shutting down API...")

app = FastAPI(
    title="SRAG Reporting Agent API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
)

@app.get("/health")
def health_check():
    return {"status": "ok", "db_ready": True}
