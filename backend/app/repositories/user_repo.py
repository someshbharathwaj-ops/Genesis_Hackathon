"""User and enrollment repositories."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import CourseEnrollment, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalars().first()


class EnrollmentRepository(BaseRepository[CourseEnrollment]):
    def __init__(self, session: AsyncSession):
        super().__init__(CourseEnrollment, session)

    async def get_enrollment(self, user_id: str, course_id: str) -> CourseEnrollment | None:
        stmt = select(CourseEnrollment).where(
            CourseEnrollment.user_id == user_id,
            CourseEnrollment.course_id == course_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_user(self, user_id: str) -> list[CourseEnrollment]:
        stmt = select(CourseEnrollment).where(CourseEnrollment.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
