"""Attempt service enforcing transaction boundaries,
immutable grading provenance, and idempotency.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RecallException, ResourceNotFoundError
from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
from app.modules.adaptive_learning.dbms_grader import DBMSDeterministicGrader
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.question_repo import QuestionRepository, QuestionVersionRepository
from app.repositories.user_repo import UserRepository
from app.services.idempotency_service import IdempotencyService


class AttemptService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.attempt_repo = AttemptRepository(session)
        self.question_repo = QuestionRepository(session)
        self.version_repo = QuestionVersionRepository(session)
        self.user_repo = UserRepository(session)
        self.idempotency_service = IdempotencyService(session)

    async def submit_attempt(
        self,
        student_id: str,
        question_id: str,
        idempotency_key: str,
        submitted_answer: dict[str, Any],
        is_hint_assisted: bool = False,
        hint_count: int = 0,
        time_spent_ms: int = 0,
        assessment_context: AssessmentContext = AssessmentContext.DIAGNOSTIC,
    ) -> tuple[Attempt, bool]:
        """Submit and deterministically grade an attempt with atomic idempotency.

        Returns (Attempt, is_replayed).
        """
        request_payload = {
            "student_id": student_id,
            "question_id": question_id,
            "submitted_answer": submitted_answer,
            "is_hint_assisted": is_hint_assisted,
            "hint_count": hint_count,
            "assessment_context": assessment_context.value,
        }

        # 1. Check idempotency replay
        existing_result = await self.idempotency_service.get_existing_result(
            idempotency_key=idempotency_key,
            request_payload=request_payload,
        )
        if existing_result:
            attempt = await self.attempt_repo.get_by_idempotency_key(idempotency_key)
            if attempt:
                return attempt, True

        # 2. Verify student exists
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        # 3. Verify question and fetch verified version
        question = await self.question_repo.get_by_id(question_id)
        if not question:
            raise ResourceNotFoundError("Question", question_id)

        # Fetch latest verified question version
        version = await self.version_repo.get_latest_verified_version(question_id)
        if not version:
            # Fall back to latest version only if unscored practice, otherwise reject
            if assessment_context == AssessmentContext.UNSCORED_PRACTICE:
                version = await self.version_repo.get_latest_version(question_id)
            if not version:
                raise RecallException(
                    status_code=422,
                    code="UNVERIFIED_EVIDENCE",
                    title="No Verified Version Available",
                    detail=(
                        f"Question '{question_id}' has no verified version "
                        "available for scored assessment."
                    ),
                )

        # 4. Check repeat count for evidence discounting
        prior_attempt_count = await self.attempt_repo.count_student_attempts_on_question(
            student_id=student_id,
            question_id=question_id,
        )

        # 5. Deterministic grading evaluation
        q_type_str = (
            question.question_type.value
            if hasattr(question.question_type, "value")
            else str(question.question_type)
        )
        grading_outcome = DBMSDeterministicGrader.grade(
            question_type=q_type_str,
            answer_key=version.answer_key,
            rubric=version.rubric,
            submitted_answer=submitted_answer,
            max_score=version.max_score,
            is_hint_assisted=is_hint_assisted,
            hint_count=hint_count,
            prior_attempt_count=prior_attempt_count,
        )

        is_correct = grading_outcome.is_correct
        score_achieved = grading_outcome.score_achieved
        max_possible_score = grading_outcome.max_possible_score

        # Provenance audit block
        provenance = grading_outcome.provenance
        provenance["question_version_id"] = version.id
        provenance["version_number"] = version.version_number
        provenance["provenance_hash"] = version.provenance_hash
        provenance["expected_answer_ref"] = version.answer_key.get("reference", "key")

        # 6. Instantiate Attempt record
        attempt = Attempt(
            idempotency_key=idempotency_key,
            student_id=student_id,
            question_id=question_id,
            question_version_id=version.id,
            assessment_context=assessment_context,
            submitted_answer=submitted_answer,
            is_hint_assisted=is_hint_assisted,
            hint_count=hint_count,
            time_spent_ms=time_spent_ms,
            submitted_at=datetime.now(UTC),
            status=AttemptStatus.GRADED,
            is_correct=is_correct,
            score_achieved=score_achieved,
            max_possible_score=max_possible_score,
            grading_provenance=provenance,
        )

        try:
            await self.attempt_repo.create(attempt)

            # 7. Record idempotency outcome in same transaction
            response_representation = {
                "attempt_id": attempt.id,
                "is_correct": is_correct,
                "score_achieved": score_achieved,
                "max_possible_score": max_possible_score,
                "status": attempt.status.value,
            }
            await self.idempotency_service.record_response(
                idempotency_key=idempotency_key,
                request_path="/api/v1/attempts",
                request_payload=request_payload,
                status_code=201,
                response_body=response_representation,
            )
            return attempt, False
        except IntegrityError:
            await self.session.rollback()
            # A concurrent worker committed an attempt with the same idempotency key
            existing = await self.attempt_repo.get_by_idempotency_key(idempotency_key)
            if existing:
                # Re-verify through idempotency service to ensure payload matched
                await self.idempotency_service.get_existing_result(
                    idempotency_key=idempotency_key,
                    request_payload=request_payload,
                )
                return existing, True
            raise
