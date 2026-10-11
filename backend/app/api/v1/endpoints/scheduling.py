"""API router for Spaced Retention Scheduling and Review Queues."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, verify_course_access, verify_student_ownership
from app.core.database import get_db
from app.models.identity import User
from app.schemas.scheduling import (
    PlanRetentionSessionRequest,
    RetentionSessionPlanResponse,
    ReviewQueueResponse,
)
from app.services.scheduling_service import SchedulingService

router = APIRouter(prefix="/courses/{course_id}/scheduling", tags=["Scheduling"])


@router.get(
    "/student/{student_id}/review-queue",
    response_model=ReviewQueueResponse,
    summary="Get Spaced Review Queue for a Student",
    description=(
        "Returns the prioritized spaced retention review queue for a student within a course. "
        "Enforces Rule 6 by locking out objectives currently within working memory cooldown."
    ),
)
async def get_review_queue(
    course_id: str,
    student_id: str,
    cooldown_seconds: float | None = Query(
        default=None,
        description="Override working memory cooldown in seconds (defaults to 3600.0s).",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ReviewQueueResponse:
    verify_student_ownership(current_user, student_id)
    await verify_course_access(course_id, current_user, session)
    service = SchedulingService(session)
    return await service.get_student_review_queue(
        course_id=course_id,
        student_id=student_id,
        cooldown_seconds=cooldown_seconds,
    )


@router.post(
    "/student/{student_id}/plan-session",
    response_model=RetentionSessionPlanResponse,
    summary="Plan a Spaced Retention Review Session",
    description=(
        "Generates a bounded retention review session plan (context: retention_review). "
        "Excludes working-memory locked items and prioritizes overdue retention targets."
    ),
)
async def plan_retention_session(
    course_id: str,
    student_id: str,
    payload: PlanRetentionSessionRequest,
    cooldown_seconds: float | None = Query(
        default=None,
        description="Override working memory cooldown in seconds.",
    ),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RetentionSessionPlanResponse:
    verify_student_ownership(current_user, student_id)
    await verify_course_access(course_id, current_user, session)
    service = SchedulingService(session)
    return await service.plan_retention_session(
        course_id=course_id,
        student_id=student_id,
        max_items=payload.max_items,
        cooldown_seconds=cooldown_seconds,
    )
