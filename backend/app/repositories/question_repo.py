"""Question and QuestionVersion repositories with versioning and provenance."""

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.question import Question, QuestionVersion, VerificationStatus
from app.repositories.base import BaseRepository


def calculate_provenance_hash(
    prompt: str, answer_key: dict[str, Any], rubric: dict[str, Any]
) -> str:
    """Calculate deterministic SHA-256 provenance hash for question version."""
    canonical_dict = {
        "prompt": prompt.strip(),
        "answer_key": answer_key,
        "rubric": rubric,
    }
    canonical_repr = json.dumps(canonical_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_repr.encode("utf-8")).hexdigest()


class QuestionRepository(BaseRepository[Question]):
    def __init__(self, session: AsyncSession):
        super().__init__(Question, session)

    async def get_with_versions(self, question_id: str) -> Question | None:
        stmt = (
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_objective(
        self, objective_id: str, only_active: bool = True
    ) -> list[Question]:
        stmt = select(Question).where(Question.objective_id == objective_id)
        if only_active:
            stmt = stmt.where(Question.is_active.is_(True))
        stmt = stmt.options(selectinload(Question.versions))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class QuestionVersionRepository(BaseRepository[QuestionVersion]):
    def __init__(self, session: AsyncSession):
        super().__init__(QuestionVersion, session)

    async def get_latest_version(self, question_id: str) -> QuestionVersion | None:
        stmt = (
            select(QuestionVersion)
            .where(QuestionVersion.question_id == question_id)
            .order_by(QuestionVersion.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_latest_verified_version(self, question_id: str) -> QuestionVersion | None:
        stmt = (
            select(QuestionVersion)
            .where(
                QuestionVersion.question_id == question_id,
                QuestionVersion.verification_status == VerificationStatus.VERIFIED,
            )
            .order_by(QuestionVersion.version_number.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_version(self, question_id: str, version_number: int) -> QuestionVersion | None:
        stmt = select(QuestionVersion).where(
            QuestionVersion.question_id == question_id,
            QuestionVersion.version_number == version_number,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
