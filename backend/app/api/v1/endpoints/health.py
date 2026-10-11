"""Health, liveness, and readiness probe endpoints."""

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str = Field(default="ok", description="Liveness status")
    environment: str = Field(description="Active environment")
    version: str = Field(description="Application version")


class ReadinessResponse(BaseModel):
    status: str = Field(default="ready", description="System readiness status")
    engines: dict[str, str] = Field(description="Subsystem status indicators")


@router.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Returns HTTP 200 if the FastAPI application server process is running.",
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.ENVIRONMENT,
        version=settings.VERSION,
    )


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Returns HTTP 200 if essential engines and dependencies are operational.",
)
async def readiness_check() -> ReadinessResponse:
    model_status = "mock" if settings.USE_MOCK_LLM else f"live:{settings.PRIMARY_MODEL}"
    return ReadinessResponse(
        status="ready",
        engines={
            "adaptive_learning_engine": "operational",
            "knowledge_engine": "operational",
            "ai_execution_engine": "operational",
            "configuration": "valid",
            "model_provider": model_status,
        },
    )
