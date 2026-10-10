"""Versioned questions endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import ResourceNotFoundError
from app.models.question import Question, QuestionVersion
from app.repositories.course_repo import LearningObjectiveRepository
from app.repositories.question_repo import (
    QuestionRepository,
    QuestionVersionRepository,
    calculate_provenance_hash,
)
from app.schemas.question import (
    QuestionCreate,
    QuestionResponse,
    QuestionVersionCreate,
    QuestionVersionResponse,
)

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    payload: QuestionCreate, db: AsyncSession = Depends(get_db)
) -> QuestionResponse:
    lo_repo = LearningObjectiveRepository(db)
    lo = await lo_repo.get_by_id(payload.objective_id)
    if not lo:
        raise ResourceNotFoundError("LearningObjective", payload.objective_id)

    q_repo = QuestionRepository(db)
    question = Question(
        objective_id=payload.objective_id,
        title=payload.title,
        question_type=payload.question_type,
        is_active=True,
    )
    await q_repo.create(question)

    # Create initial version
    initial = payload.initial_version
    prov_hash = calculate_provenance_hash(
        prompt=initial.prompt,
        answer_key=initial.answer_key,
        rubric=initial.rubric,
    )
    version = QuestionVersion(
        question_id=question.id,
        version_number=1,
        prompt=initial.prompt,
        difficulty=initial.difficulty,
        max_score=initial.max_score,
        options=initial.options,
        answer_key=initial.answer_key,
        rubric=initial.rubric,
        explanation=initial.explanation,
        verification_status=initial.verification_status,
        verified_by=initial.verified_by,
        provenance_hash=prov_hash,
    )
    v_repo = QuestionVersionRepository(db)
    await v_repo.create(version)

    full_q = await q_repo.get_with_versions(question.id)
    return QuestionResponse.model_validate(full_q)


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: str, db: AsyncSession = Depends(get_db)) -> QuestionResponse:
    q_repo = QuestionRepository(db)
    question = await q_repo.get_with_versions(question_id)
    if not question:
        raise ResourceNotFoundError("Question", question_id)
    return QuestionResponse.model_validate(question)


@router.post(
    "/{question_id}/versions",
    response_model=QuestionVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_question_version(
    question_id: str, payload: QuestionVersionCreate, db: AsyncSession = Depends(get_db)
) -> QuestionVersionResponse:
    q_repo = QuestionRepository(db)
    question = await q_repo.get_by_id(question_id)
    if not question:
        raise ResourceNotFoundError("Question", question_id)

    v_repo = QuestionVersionRepository(db)
    latest = await v_repo.get_latest_version(question_id)
    next_version = (latest.version_number + 1) if latest else 1

    prov_hash = calculate_provenance_hash(
        prompt=payload.prompt,
        answer_key=payload.answer_key,
        rubric=payload.rubric,
    )

    version = QuestionVersion(
        question_id=question_id,
        version_number=next_version,
        prompt=payload.prompt,
        difficulty=payload.difficulty,
        max_score=payload.max_score,
        options=payload.options,
        answer_key=payload.answer_key,
        rubric=payload.rubric,
        explanation=payload.explanation,
        verification_status=payload.verification_status,
        verified_by=payload.verified_by,
        provenance_hash=prov_hash,
    )
    created = await v_repo.create(version)
    return QuestionVersionResponse.model_validate(created)


@router.get("/objective/{objective_id}", response_model=list[QuestionResponse])
async def list_questions_for_objective(
    objective_id: str, db: AsyncSession = Depends(get_db)
) -> list[QuestionResponse]:
    q_repo = QuestionRepository(db)
    questions = await q_repo.list_by_objective(objective_id)
    return [QuestionResponse.model_validate(q) for q in questions]
