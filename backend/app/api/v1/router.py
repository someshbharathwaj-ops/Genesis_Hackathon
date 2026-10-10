"""API v1 Central Router."""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_v1_router = APIRouter()

# Mount health & readiness probes
api_v1_router.include_router(health.router)
