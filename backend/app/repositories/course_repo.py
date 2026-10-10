"""Course, Topic, and LearningObjective repositories."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.curriculum import LearningObjective, Topic
from app.models.identity import Course
from app.repositories.base import BaseRepository


class CourseRepository(BaseRepository[Course]):
    def __init__(self, session: AsyncSession):
        super().__init__(Course, session)

    async def get_by_code(self, code: str) -> Course | None:
        stmt = select(Course).where(Course.code == code)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_with_topics(self, course_id: str) -> Course | None:
        stmt = (
            select(Course)
            .where(Course.id == course_id)
            .options(selectinload(Course.topics).selectinload(Topic.objectives))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class TopicRepository(BaseRepository[Topic]):
    def __init__(self, session: AsyncSession):
        super().__init__(Topic, session)

    async def list_by_course(self, course_id: str) -> list[Topic]:
        stmt = (
            select(Topic)
            .where(Topic.course_id == course_id)
            .order_by(Topic.order_index)
            .options(selectinload(Topic.objectives))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class LearningObjectiveRepository(BaseRepository[LearningObjective]):
    def __init__(self, session: AsyncSession):
        super().__init__(LearningObjective, session)

    async def list_by_topic(self, topic_id: str) -> list[LearningObjective]:
        stmt = (
            select(LearningObjective)
            .where(LearningObjective.topic_id == topic_id)
            .order_by(LearningObjective.order_index)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_code(self, topic_id: str, code: str) -> LearningObjective | None:
        stmt = select(LearningObjective).where(
            LearningObjective.topic_id == topic_id,
            LearningObjective.code == code,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
