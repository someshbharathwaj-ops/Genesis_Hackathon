"""FastAPI endpoint for Grounded AI Tutor concept explanations."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.tutor import TutorQueryRequest, TutorQueryResponse
from app.services.tutor_service import TutorService

router = APIRouter(prefix="/courses/{course_id}/tutor", tags=["Tutor"])


@router.post(
    "/ask",
    response_model=TutorQueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query Grounded AI Tutor with course syllabus grounding",
)
async def ask_course_tutor(
    course_id: str,
    request: TutorQueryRequest,
    session: AsyncSession = Depends(get_db),
) -> TutorQueryResponse:
    """Submit a question to the Grounded AI Tutor.

    - Performs server-side scored assessment lockout checks.
    - Retrieves candidate excerpts strictly from the specified course.
    - Formulates bounded prompt with source citations.
    - Returns pedagogical answer or explicit abstention.
    - Guaranteed to never alter student grades, attempts, or mastery state.
    """
    service = TutorService(session=session)
    return await service.ask_tutor(
        course_id=course_id,
        student_id=request.student_id,
        query=request.query,
        objective_id=request.objective_id,
    )
