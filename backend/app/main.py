"""Recall Modular Monolith FastAPI Application Entrypoint."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import api_v1_router
from app.core.config import settings
from app.core.errors import (
    ProblemDetails,
    RecallException,
    http_exception_handler,
    recall_exception_handler,
    validation_exception_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager."""
    # Initialization of engines, connection pools, and readiness verifications
    yield
    # Graceful shutdown of connection pools


def create_application() -> FastAPI:
    """Factory creating and configuring the FastAPI instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="Institutional-grade grounded adaptive learning platform backend.",
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
        responses={
            422: {"model": ProblemDetails, "description": "Validation Error"},
            500: {"model": ProblemDetails, "description": "Internal Server Error"},
        },
    )

    # CORS configuration
    origins = (
        settings.ALLOWED_ORIGINS
        if isinstance(settings.ALLOWED_ORIGINS, list)
        else [settings.ALLOWED_ORIGINS]
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # RFC 7807 Exception Handlers
    app.add_exception_handler(RecallException, recall_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore[arg-type]

    # Mount API v1 router
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    return app


app = create_application()
