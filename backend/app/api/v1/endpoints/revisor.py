"""API router for Grounded Revisor evidence review and adversarial audits."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.revisor import RevisorReviewRequest, RevisorReviewResponse
from app.services.revisor_service import RevisorService

router = APIRouter(prefix="/courses/{course_id}/revisor", tags=["Revisor"])


@router.post(
    "/review",
    response_model=RevisorReviewResponse,
    summary="Audit Candidate Explanation or Misconception via Revisor",
    description=(
        "Cross-examines a candidate explanation, student answer, or misconception claim against "
        "official course materials. Enforces server-side scored assessment lockout."
    ),
)
async def review_candidate_text(
    course_id: str,
    payload: RevisorReviewRequest,
    session: AsyncSession = Depends(get_db),
) -> RevisorReviewResponse:
    service = RevisorService(session)
    return await service.review_explanation(
        course_id=course_id,
        student_id=payload.student_id,
        candidate_text=payload.candidate_text,
        query_or_topic=payload.query_or_topic,
        objective_id=payload.objective_id,
        check_deterministic_logic=payload.check_deterministic_logic,
    )
