# HealthChecker/app/main.py
"""
main.py  –  FastAPI application entry point for HealthChecker.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from pathlib import Path
from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ROOT_ENV if _ROOT_ENV.exists() else None)

from app.api import api_router
from app.tasks.ai_tasks import start_worker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting HealthChecker API…")
    await start_worker()
    yield
    logger.info("Shutting down HealthChecker API…")


app = FastAPI(
    title="HealthChecker API",
    version="1.0.0",
    description="Simplified health prediction CRUD backend.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
        headers={
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        },
    )


app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "HealthChecker API"}
