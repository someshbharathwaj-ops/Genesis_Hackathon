"""Repositories for CourseDocument and DocumentChunk entities."""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import CourseDocument, DocumentChunk
from app.repositories.base import BaseRepository


class CourseDocumentRepository(BaseRepository[CourseDocument]):
    def __init__(self, session: AsyncSession):
        super().__init__(CourseDocument, session)

    async def get_by_course_and_hash(
        self, course_id: str, content_hash: str
    ) -> CourseDocument | None:
        """Find an existing document by course and content hash for deduplication."""
        stmt = select(CourseDocument).where(
            CourseDocument.course_id == course_id,
            CourseDocument.content_hash == content_hash,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_by_course(self, course_id: str) -> list[CourseDocument]:
        """List all documents belonging to a course."""
        stmt = (
            select(CourseDocument)
            .where(CourseDocument.course_id == course_id)
            .order_by(CourseDocument.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_chunks(self, document_id: str) -> CourseDocument | None:
        """Fetch document with eagerly loaded chunks."""
        stmt = (
            select(CourseDocument)
            .where(CourseDocument.id == document_id)
            .options(selectinload(CourseDocument.chunks))
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    def __init__(self, session: AsyncSession):
        super().__init__(DocumentChunk, session)

    async def list_by_course(self, course_id: str) -> list[DocumentChunk]:
        """Fetch all chunks belonging to a course for tenant-isolated retrieval."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.course_id == course_id)
            .options(selectinload(DocumentChunk.document))
            .order_by(DocumentChunk.page_number.asc(), DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_document(self, document_id: str) -> list[DocumentChunk]:
        """Fetch chunks for a specific document."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document."""
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        return int(result.rowcount)
