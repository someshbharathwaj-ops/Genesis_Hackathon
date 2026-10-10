"""API endpoints for Course Document Ingestion and Knowledge Retrieval."""

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.document import (
    CourseDocumentDetailResponse,
    CourseDocumentResponse,
    RetrievalQueryRequest,
    RetrievalResponse,
)
from app.services.knowledge_service import KnowledgeService

router = APIRouter(prefix="/courses", tags=["Knowledge Engine & Document Ingestion"])


@router.post(
    "/{course_id}/documents/upload",
    response_model=CourseDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_course_document(
    course_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> CourseDocumentResponse:
    """Upload and ingest a course material document (PDF or TXT) with repeat-safety."""
    service = KnowledgeService(db)
    file_bytes = await file.read()
    filename = file.filename or "uploaded_document.pdf"
    mime_type = file.content_type

    return await service.ingest_document(
        course_id=course_id,
        filename=filename,
        file_bytes=file_bytes,
        mime_type=mime_type,
    )


@router.get(
    "/{course_id}/documents",
    response_model=list[CourseDocumentResponse],
)
async def list_course_documents(
    course_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[CourseDocumentResponse]:
    """List all ingested documents for a specific course."""
    service = KnowledgeService(db)
    return await service.list_course_documents(course_id=course_id)


@router.get(
    "/{course_id}/documents/{document_id}",
    response_model=CourseDocumentDetailResponse,
)
async def get_course_document_detail(
    course_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> CourseDocumentDetailResponse:
    """Retrieve full document metadata and extracted semantic chunks with page provenance."""
    service = KnowledgeService(db)
    return await service.get_document_detail(course_id=course_id, document_id=document_id)


@router.delete(
    "/{course_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_course_document(
    course_id: str,
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a course document and all its indexed chunks."""
    service = KnowledgeService(db)
    await service.delete_document(course_id=course_id, document_id=document_id)


@router.post(
    "/{course_id}/knowledge/retrieve",
    response_model=RetrievalResponse,
)
async def retrieve_course_knowledge(
    course_id: str,
    payload: RetrievalQueryRequest,
    db: AsyncSession = Depends(get_db),
) -> RetrievalResponse:
    """Execute tenant-isolated semantic vector retrieval against course lecture chunks."""
    service = KnowledgeService(db)
    return await service.retrieve_knowledge(
        course_id=course_id,
        query=payload.query,
        top_k=payload.top_k,
        similarity_threshold=payload.similarity_threshold,
    )
