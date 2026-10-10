"""Evidence and Bounded Diagnosis API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.diagnosis import (
    CourseDiagnosticSummaryResponse,
    DiagnosticSessionPlanRequest,
    DiagnosticSessionPlanResponse,
    ObjectiveDiagnosticResponse,
)
from app.services.diagnosis_service import DiagnosisService

router = APIRouter(prefix="/diagnosis", tags=["Evidence & Bounded Diagnosis"])


@router.get(
    "/student/{student_id}/objective/{objective_id}",
    response_model=ObjectiveDiagnosticResponse,
)
async def get_student_objective_diagnosis(
    student_id: str,
    objective_id: str,
    db: AsyncSession = Depends(get_db),
) -> ObjectiveDiagnosticResponse:
    """Evaluate explainable bounded diagnosis and evidence ledger for a student objective."""
    service = DiagnosisService(db)
    return await service.get_objective_diagnosis(student_id=student_id, objective_id=objective_id)


@router.get(
    "/student/{student_id}/course/{course_id}",
    response_model=CourseDiagnosticSummaryResponse,
)
async def get_student_course_diagnosis(
    student_id: str,
    course_id: str,
    db: AsyncSession = Depends(get_db),
) -> CourseDiagnosticSummaryResponse:
    """Evaluate course-wide diagnostic summary, root-cause gaps, and prerequisite traces."""
    service = DiagnosisService(db)
    return await service.get_course_diagnosis(student_id=student_id, course_id=course_id)


@router.post(
    "/session/plan",
    response_model=DiagnosticSessionPlanResponse,
)
async def plan_diagnostic_session(
    payload: DiagnosticSessionPlanRequest,
    db: AsyncSession = Depends(get_db),
) -> DiagnosticSessionPlanResponse:
    """Generate a bounded diagnostic probing session plan (strictly <= 5 questions)."""
    service = DiagnosisService(db)
    return await service.create_session_plan(
        student_id=payload.student_id,
        course_id=payload.course_id,
        target_objective_id=payload.target_objective_id,
    )
