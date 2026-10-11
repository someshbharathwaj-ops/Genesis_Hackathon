"""Ingest all DBMS theory documents into the Recall database and knowledge base."""

import asyncio
import os
import sys

# Ensure backend is on sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import AsyncSessionLocal
from app.models.identity import Course
from app.models.document import DocumentStatus
from app.repositories.course_repo import CourseRepository
from app.services.knowledge_service import KnowledgeService
from sqlalchemy import select


async def main():
    print("=" * 60)
    print("INGESTING DBMS COURSE DOCUMENTS INTO RECALL KNOWLEDGE BASE")
    print("=" * 60)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    theory_dir = os.path.join(repo_root, "DBMS", "theory")
    knowledge_dir = os.path.join(repo_root, "knowledge", "CS340")

    async with AsyncSessionLocal() as session:
        # 1. Locate Course CS340
        stmt = select(Course).where(Course.code == "CS340")
        res = await session.execute(stmt)
        course = res.scalar_one_or_none()

        if not course:
            print("ERROR: Course CS340 not found in database! Creating CS340...")
            course_repo = CourseRepository(session)
            course = await course_repo.create_course(
                code="CS340",
                title="Database Management Systems",
                description="Relational database models, normal forms, transaction management, and SQL.",
                instructor_id=None,
            )
            print(f"Created Course CS340 with ID: {course.id}")
        else:
            print(f"Found Course CS340: ID={course.id}, Title='{course.title}'")

        service = KnowledgeService(session)

        # Gather target files
        candidate_files = []
        if os.path.isdir(theory_dir):
            for fname in sorted(os.listdir(theory_dir)):
                fpath = os.path.join(theory_dir, fname)
                if os.path.isfile(fpath):
                    candidate_files.append((fname, fpath))

        if os.path.isdir(knowledge_dir):
            for fname in sorted(os.listdir(knowledge_dir)):
                fpath = os.path.join(knowledge_dir, fname)
                if os.path.isfile(fpath):
                    candidate_files.append((fname, fpath))

        print(f"\nDiscovered {len(candidate_files)} candidate course files to process.\n")

        indexed_count = 0
        skipped_count = 0
        failed_count = 0

        for fname, fpath in candidate_files:
            # Skip massive 1400-page textbook or scanned image PDFs without text to keep ingestion fast
            size_mb = os.path.getsize(fpath) / (1024 * 1024)
            if size_mb > 10 and "Concepts" in fname:
                print(f"[-] Skipping massive full textbook: {fname} ({size_mb:.1f} MB) to optimize memory and response time.")
                skipped_count += 1
                continue
            if size_mb > 50:
                print(f"[-] Skipping massive scanned file: {fname} ({size_mb:.1f} MB).")
                skipped_count += 1
                continue

            try:
                with open(fpath, "rb") as f:
                    file_bytes = f.read()

                print(f"[+] Ingesting: {fname} ({len(file_bytes)} bytes)...", end=" ", flush=True)
                doc_resp = await service.ingest_document(
                    course_id=course.id,
                    filename=fname,
                    file_bytes=file_bytes,
                )

                if doc_resp.status == DocumentStatus.INDEXED:
                    print(f"SUCCESS -> {doc_resp.chunk_count} chunks indexed across {doc_resp.page_count} pages.")
                    indexed_count += 1
                elif doc_resp.status == DocumentStatus.EMPTY:
                    print(f"EMPTY -> No extractable text found.")
                    skipped_count += 1
                else:
                    print(f"STATUS -> {doc_resp.status} ({doc_resp.error_message})")
                    skipped_count += 1

            except Exception as exc:
                print(f"FAILED -> {exc}")
                failed_count += 1

        print("\n" + "=" * 60)
        print(f"INGESTION COMPLETE:")
        print(f"  Successfully Indexed: {indexed_count} documents")
        print(f"  Skipped (Empty/Oversized): {skipped_count} documents")
        print(f"  Failed: {failed_count} documents")
        print("=" * 60)

        # Retrieve a sample test query to verify vector search works over the ingested knowledge
        print("\n[VERIFY] Testing Semantic Vector Retrieval on Ingested Knowledge:")
        test_query = "What is BCNF and how does it differ from 3NF?"
        retrieval = await service.retrieve_knowledge(
            course_id=course.id,
            query=test_query,
            top_k=3,
        )
        print(f"Query: '{test_query}'")
        print(f"Matches found: {len(retrieval.matches)}")
        for i, m in enumerate(retrieval.matches, 1):
            print(f"  Match #{i}: [{m.document_filename}, Page {m.page_number}] Score: {m.similarity_score:.3f}")
            snippet = m.content[:100].replace("\n", " ")
            print(f"    Excerpt: \"{snippet}...\"")


if __name__ == "__main__":
    asyncio.run(main())
