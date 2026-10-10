"""Idempotency record repository for locking and response caching."""


from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attempt import IdempotencyRecord
from app.repositories.base import BaseRepository


class IdempotencyRepository(BaseRepository[IdempotencyRecord]):
    def __init__(self, session: AsyncSession):
        super().__init__(IdempotencyRecord, session)

    async def get_by_key(self, idempotency_key: str) -> IdempotencyRecord | None:
        stmt = select(IdempotencyRecord).where(
            IdempotencyRecord.idempotency_key == idempotency_key
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()
