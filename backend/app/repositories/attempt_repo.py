"""Attempt repository for recording and auditing immutable submissions."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.attempt import Attempt
from app.repositories.base import BaseRepository


class AttemptRepository(BaseRepository[Attempt]):
    def __init__(self, session: AsyncSession):
        super().__init__(Attempt, session)

    async def get_by_idempotency_key(self, idempotency_key: str) -> Attempt | None:
        stmt = (
            select(Attempt)
            .where(Attempt.idempotency_key == idempotency_key)
            .options(selectinload(Attempt.question_version))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_student_and_question(
        self, student_id: str, question_id: str
    ) -> list[Attempt]:
        stmt = (
            select(Attempt)
            .where(
                Attempt.student_id == student_id,
                Attempt.question_id == question_id,
            )
            .order_by(Attempt.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_student_attempts_on_question(self, student_id: str, question_id: str) -> int:
        stmt = select(func.count(Attempt.id)).where(
            Attempt.student_id == student_id,
            Attempt.question_id == question_id,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one_or_none() or 0)

    async def list_student_attempts(
        self, student_id: str, limit: int = 50, offset: int = 0
    ) -> list[Attempt]:
        stmt = (
            select(Attempt)
            .where(Attempt.student_id == student_id)
            .order_by(Attempt.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_student_for_objectives(
        self, student_id: str, objective_ids: list[str]
    ) -> list[Attempt]:
        if not objective_ids:
            return []
        from app.models.question import Question

        stmt = (
            select(Attempt)
            .join(Question, Attempt.question_id == Question.id)
            .where(
                Attempt.student_id == student_id,
                Question.objective_id.in_(objective_ids),
            )
            .order_by(Attempt.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_student_attempt(self, student_id: str) -> Attempt | None:
        from app.models.attempt import AttemptStatus

        stmt = (
            select(Attempt)
            .where(
                Attempt.student_id == student_id,
                Attempt.status == AttemptStatus.IN_PROGRESS,
            )
            .order_by(Attempt.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
