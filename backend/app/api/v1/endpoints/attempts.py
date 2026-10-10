"""Attempt submission and provenance inspection endpoints."""

from fastapi import APIRouter, Depends, Header, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ResourceNotFoundError
from app.repositories.attempt_repo import AttemptRepository
from app.schemas.attempt import AttemptCreate, AttemptResponse
from app.services.attempt_service import AttemptService

router = APIRouter(prefix="/attempts", tags=["Attempts & Provenance"])


@router.post("", response_model=AttemptResponse)
async def submit_attempt(
    payload: AttemptCreate,
    response: Response,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
) -> AttemptResponse:
    service = AttemptService(db)
    attempt, is_replayed = await service.submit_attempt(
        student_id=payload.student_id,
        question_id=payload.question_id,
        idempotency_key=idempotency_key,
        submitted_answer=payload.submitted_answer,
        is_hint_assisted=payload.is_hint_assisted,
        hint_count=payload.hint_count,
        time_spent_ms=payload.time_spent_ms,
        assessment_context=payload.assessment_context,
    )

    if is_replayed:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_201_CREATED

    return AttemptResponse.model_validate(attempt)


@router.get("/{attempt_id}", response_model=AttemptResponse)
async def get_attempt(attempt_id: str, db: AsyncSession = Depends(get_db)) -> AttemptResponse:
    repo = AttemptRepository(db)
    attempt = await repo.get_by_id(attempt_id)
    if not attempt:
        raise ResourceNotFoundError("Attempt", attempt_id)
    return AttemptResponse.model_validate(attempt)


@router.get("/student/{student_id}", response_model=list[AttemptResponse])
async def list_student_attempts(
    student_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> list[AttemptResponse]:
    repo = AttemptRepository(db)
    attempts = await repo.list_student_attempts(student_id, limit=limit, offset=offset)
    return [AttemptResponse.model_validate(a) for a in attempts]
