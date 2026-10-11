"""API v1 Central Router mounting all domain engine endpoints."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    attempts,
    courses,
    diagnosis,
    documents,
    health,
    mastery,
    questions,
    tutor,
    users,
)

api_v1_router = APIRouter()

# Health & readiness
api_v1_router.include_router(health.router)

# Domain engine endpoints
api_v1_router.include_router(users.router)
api_v1_router.include_router(courses.router)
api_v1_router.include_router(questions.router)
api_v1_router.include_router(attempts.router)
api_v1_router.include_router(mastery.router)
api_v1_router.include_router(diagnosis.router)
api_v1_router.include_router(documents.router)
api_v1_router.include_router(tutor.router)
