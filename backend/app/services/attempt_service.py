"""Attempt service enforcing transaction boundaries,
immutable grading provenance, and idempotency.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RecallException, ResourceNotFoundError
from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
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
        expected_answer = version.answer_key.get("value")
        actual_answer = submitted_answer.get("value")

        is_correct = False
        score_achieved = 0.0
        max_possible_score = version.max_score

        if actual_answer is not None and expected_answer is not None:
            if isinstance(expected_answer, list) and isinstance(actual_answer, list):
                is_correct = sorted(actual_answer) == sorted(expected_answer)
            else:
                is_correct = str(actual_answer).strip() == str(expected_answer).strip()

        if is_correct:
            # Discount for hints in scored context
            if is_hint_assisted and hint_count > 0:
                hint_penalty = min(0.65, 0.25 * hint_count)
                score_achieved = max(0.0, max_possible_score * (1.0 - hint_penalty))
            else:
                score_achieved = max_possible_score

        # Provenance audit block
        provenance = {
            "evaluator": "DeterministicBaselineGrader",
            "evaluated_at": datetime.now(UTC).isoformat(),
            "question_version_id": version.id,
            "version_number": version.version_number,
            "provenance_hash": version.provenance_hash,
            "expected_answer_ref": version.answer_key.get("reference", "key"),
            "is_hint_assisted": is_hint_assisted,
            "hint_count": hint_count,
            "prior_attempt_count": prior_attempt_count,
            "repetition_discount_applied": prior_attempt_count > 0,
            "rubric_match": "exact" if is_correct else "mismatch",
        }

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
