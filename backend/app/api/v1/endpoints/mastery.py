"""Mastery API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.mastery import CourseMasterySummaryResponse, ObjectiveMasteryResponse
from app.services.mastery_service import MasteryService

router = APIRouter(prefix="/mastery", tags=["Mastery & Adaptive Learning"])


@router.get(
    "/student/{student_id}/course/{course_id}",
    response_model=CourseMasterySummaryResponse,
)
async def get_student_course_mastery(
    student_id: str,
    course_id: str,
    db: AsyncSession = Depends(get_db),
) -> CourseMasterySummaryResponse:
    """Retrieve full course mastery profile and objective breakdown for a student."""
    service = MasteryService(db)
    return await service.get_course_mastery(student_id=student_id, course_id=course_id)


@router.get(
    "/student/{student_id}/objective/{objective_id}",
    response_model=ObjectiveMasteryResponse,
)
async def get_student_objective_mastery(
    student_id: str,
    objective_id: str,
    db: AsyncSession = Depends(get_db),
) -> ObjectiveMasteryResponse:
    """Retrieve granular mastery details for a single objective."""
    service = MasteryService(db)
    return await service.get_objective_mastery(
        student_id=student_id, objective_id=objective_id
    )
