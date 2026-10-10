"""Knowledge Engine service orchestrating document ingestion, chunking, and isolated retrieval."""

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.models.document import CourseDocument, DocumentChunk, DocumentStatus
from app.modules.knowledge_engine.chunker import SemanticChunker
from app.modules.knowledge_engine.document_extractor import DocumentExtractor
from app.modules.knowledge_engine.embedding_provider import (
    BaseEmbeddingProvider,
    get_embedding_provider,
)
from app.modules.knowledge_engine.retrieval_engine import KnowledgeRetrievalEngine
from app.repositories.course_repo import CourseRepository
from app.repositories.document_repo import CourseDocumentRepository, DocumentChunkRepository
from app.schemas.document import (
    CourseDocumentDetailResponse,
    CourseDocumentResponse,
    DocumentChunkResponse,
    RetrievalMatchResponse,
    RetrievalResponse,
)


class KnowledgeService:
    """Service orchestrating document lifecycle, semantic chunking, and course-scoped RAG."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: BaseEmbeddingProvider | None = None,
    ):
        self.session = session
        self.course_repo = CourseRepository(session)
        self.doc_repo = CourseDocumentRepository(session)
        self.chunk_repo = DocumentChunkRepository(session)
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def ingest_document(
        self,
        course_id: str,
        filename: str,
        file_bytes: bytes,
        mime_type: str | None = None,
    ) -> CourseDocumentResponse:
        """Ingest a course document repeat-safely with text extraction, chunking, and embedding."""
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        content_hash = hashlib.sha256(file_bytes).hexdigest()

        # 1. Repeat-safe idempotency check: check if already indexed
        existing_doc = await self.doc_repo.get_by_course_and_hash(course_id, content_hash)
        if existing_doc and existing_doc.status == DocumentStatus.INDEXED:
            existing_chunks = await self.chunk_repo.list_by_document(existing_doc.id)
            return CourseDocumentResponse(
                id=existing_doc.id,
                course_id=existing_doc.course_id,
                filename=existing_doc.filename,
                content_hash=existing_doc.content_hash,
                mime_type=existing_doc.mime_type,
                file_size_bytes=existing_doc.file_size_bytes,
                page_count=existing_doc.page_count,
                status=existing_doc.status,
                error_message=existing_doc.error_message,
                chunk_count=len(existing_chunks),
                created_at=existing_doc.created_at,
            )

        # 2. Extract text from document
        extraction = DocumentExtractor.extract_from_bytes(
            file_bytes=file_bytes,
            filename=filename,
            mime_type=mime_type,
        )

        doc = existing_doc or CourseDocument(
            course_id=course_id,
            filename=filename,
            content_hash=content_hash,
            mime_type=mime_type or "application/octet-stream",
            file_size_bytes=len(file_bytes),
            page_count=extraction.page_count,
            status=DocumentStatus.PENDING,
        )

        if not existing_doc:
            await self.doc_repo.create(doc)

        # If document is empty
        if extraction.is_empty:
            doc.status = DocumentStatus.EMPTY
            doc.error_message = "No extractable text found in document."
            await self.session.commit()
            return CourseDocumentResponse(
                id=doc.id,
                course_id=doc.course_id,
                filename=doc.filename,
                content_hash=doc.content_hash,
                mime_type=doc.mime_type,
                file_size_bytes=doc.file_size_bytes,
                page_count=doc.page_count,
                status=doc.status,
                error_message=doc.error_message,
                chunk_count=0,
                created_at=doc.created_at,
            )

        # 3. Clean up any previous chunks if re-processing
        if existing_doc:
            await self.chunk_repo.delete_by_document(doc.id)

        # 4. Generate semantic chunks
        chunk_items = SemanticChunker.chunk_document(
            text_by_page=extraction.text_by_page,
            filename=filename,
        )

        # 5. Generate vector embeddings
        texts = [c.content for c in chunk_items]
        embeddings = await self.embedding_provider.embed_texts(texts)

        # 6. Save chunks
        for item, emb in zip(chunk_items, embeddings, strict=False):
            chunk_record = DocumentChunk(
                document_id=doc.id,
                course_id=course_id,
                chunk_index=item.chunk_index,
                page_number=item.page_number,
                content=item.content,
                token_count=item.token_count,
                embedding=emb,
                metadata_attributes=item.metadata_attributes,
            )
            self.session.add(chunk_record)

        doc.status = DocumentStatus.INDEXED
        doc.error_message = None
        doc.page_count = extraction.page_count
        await self.session.commit()
        await self.session.refresh(doc)

        return CourseDocumentResponse(
            id=doc.id,
            course_id=doc.course_id,
            filename=doc.filename,
            content_hash=doc.content_hash,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            page_count=doc.page_count,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=len(chunk_items),
            created_at=doc.created_at,
        )

    async def list_course_documents(self, course_id: str) -> list[CourseDocumentResponse]:
        """List all documents uploaded to a course."""
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        docs = await self.doc_repo.list_by_course(course_id)
        result: list[CourseDocumentResponse] = []
        for d in docs:
            chunks = await self.chunk_repo.list_by_document(d.id)
            result.append(
                CourseDocumentResponse(
                    id=d.id,
                    course_id=d.course_id,
                    filename=d.filename,
                    content_hash=d.content_hash,
                    mime_type=d.mime_type,
                    file_size_bytes=d.file_size_bytes,
                    page_count=d.page_count,
                    status=d.status,
                    error_message=d.error_message,
                    chunk_count=len(chunks),
                    created_at=d.created_at,
                )
            )
        return result

    async def get_document_detail(
        self, course_id: str, document_id: str
    ) -> CourseDocumentDetailResponse:
        """Fetch full details and chunks of a document."""
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        doc = await self.doc_repo.get_with_chunks(document_id)
        if not doc or doc.course_id != course_id:
            raise ResourceNotFoundError("CourseDocument", document_id)

        chunks_resp = [
            DocumentChunkResponse(
                id=c.id,
                document_id=c.document_id,
                course_id=c.course_id,
                chunk_index=c.chunk_index,
                page_number=c.page_number,
                content=c.content,
                token_count=c.token_count,
                metadata_attributes=c.metadata_attributes,
                created_at=c.created_at,
            )
            for c in doc.chunks
        ]

        return CourseDocumentDetailResponse(
            id=doc.id,
            course_id=doc.course_id,
            filename=doc.filename,
            content_hash=doc.content_hash,
            mime_type=doc.mime_type,
            file_size_bytes=doc.file_size_bytes,
            page_count=doc.page_count,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=len(chunks_resp),
            created_at=doc.created_at,
            chunks=chunks_resp,
        )

    async def delete_document(self, course_id: str, document_id: str) -> bool:
        """Delete a document and its chunks."""
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        doc = await self.doc_repo.get_by_id(document_id)
        if not doc or doc.course_id != course_id:
            raise ResourceNotFoundError("CourseDocument", document_id)

        await self.doc_repo.delete(doc)
        await self.session.commit()
        return True

    async def retrieve_knowledge(
        self,
        course_id: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
    ) -> RetrievalResponse:
        """Execute tenant-isolated semantic retrieval against course curriculum chunks."""
        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        # 1. Generate query embedding
        query_vector = await self.embedding_provider.embed_query(query)

        # 2. Fetch candidate chunks strictly within this course
        chunks = await self.chunk_repo.list_by_course(course_id)

        # 3. Retrieve and score matches with isolation guarantees
        result = KnowledgeRetrievalEngine.retrieve_chunks(
            query=query,
            query_vector=query_vector,
            chunks=chunks,
            course_id=course_id,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

        matches_resp = [
            RetrievalMatchResponse(
                chunk_id=m.chunk_id,
                document_id=m.document_id,
                document_filename=m.document_filename,
                page_number=m.page_number,
                content=m.content,
                similarity_score=m.similarity_score,
                citation=m.citation,
                metadata_attributes=m.metadata_attributes,
            )
            for m in result.matches
        ]

        return RetrievalResponse(
            query=result.query,
            course_id=result.course_id,
            total_candidates=result.total_candidates,
            matches=matches_resp,
            abstention_recommended=result.abstention_recommended,
            explanation=result.explanation,
        )
