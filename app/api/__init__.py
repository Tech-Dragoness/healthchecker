# HealthChecker/app/api/__init__.py
from fastapi import APIRouter
from app.api.routes.applications import router as applications_router

api_router = APIRouter(prefix="/api")
api_router.include_router(applications_router)
