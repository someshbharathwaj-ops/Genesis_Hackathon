"""Generalized Multi-Course Knowledge Ingestion CLI for Recall.

Supports ingesting documents (.pdf, .md, .txt, .docx, .pptx) for ANY course.
Supports:
  1. Direct course + directory ingestion:
     python scripts/ingest_course_materials.py --course CS101 --dir ./path/to/materials --title "Intro to CS"
  2. Multi-course batch discovery:
     python scripts/ingest_course_materials.py --scan-dir ./knowledge
     (Ingests every subfolder ./knowledge/<COURSE_CODE>/ into its respective course)
  3. Dry-run estimation:
     python scripts/ingest_course_materials.py --course CS340 --dir ./DBMS/theory --dry-run
"""

import argparse
import asyncio
import os
import sys

# Ensure backend directory is in python search path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.identity import Course
from app.models.document import DocumentStatus
from app.modules.knowledge_engine.document_extractor import DocumentExtractor
from app.repositories.course_repo import CourseRepository
from app.services.knowledge_service import KnowledgeService


async def get_or_create_course(session, course_code: str, title: str | None = None, description: str | None = None) -> Course:
    """Find course by code or create it dynamically."""
    stmt = select(Course).where(Course.code == course_code.upper())
    res = await session.execute(stmt)
    course = res.scalar_one_or_none()

    if not course:
        repo = CourseRepository(session)
        course_title = title or f"Course {course_code.upper()}"
        course_desc = description or f"Academic course curriculum and learning materials for {course_code.upper()}."
        course = await repo.create_course(
            code=course_code.upper(),
            title=course_title,
            description=course_desc,
            instructor_id=None,
        )
        print(f"[+] Created new course: {course.code} - '{course.title}' (ID: {course.id})")
    else:
        print(f"[*] Found existing course: {course.code} - '{course.title}' (ID: {course.id})")

    return course


def discover_files(directory_path: str, recursive: bool = True) -> list[tuple[str, str]]:
    """Discover all supported document files in a directory."""
    supported = DocumentExtractor.SUPPORTED_EXTENSIONS
    matched = []

    if not os.path.isdir(directory_path):
        return matched

    if recursive:
        for root, _, files in os.walk(directory_path):
            for f in sorted(files):
                _, ext = os.path.splitext(f.lower())
                if ext in supported:
                    matched.append((f, os.path.join(root, f)))
    else:
        for f in sorted(os.listdir(directory_path)):
            fpath = os.path.join(directory_path, f)
            if os.path.isfile(fpath):
                _, ext = os.path.splitext(f.lower())
                if ext in supported:
                    matched.append((f, fpath))

    return matched


async def ingest_files_for_course(
    session,
    course: Course,
    files: list[tuple[str, str]],
    max_size_mb: float = 30.0,
    dry_run: bool = False,
):
    """Ingest a list of files into a specific course knowledge base."""
    service = KnowledgeService(session)
    print(f"\n--- Ingesting {len(files)} files into Course [{course.code}] ---")

    indexed = 0
    skipped = 0
    failed = 0

    for fname, fpath in files:
        size_bytes = os.path.getsize(fpath)
        size_mb = size_bytes / (1024 * 1024)

        if size_mb > max_size_mb:
            print(f"[-] [SKIP] {fname} ({size_mb:.1f} MB exceeds max size cutoff of {max_size_mb} MB)")
            skipped += 1
            continue

        if dry_run:
            print(f"[*] [DRY-RUN] Would extract & index {fname} ({size_mb:.2f} MB)")
            indexed += 1
            continue

        try:
            with open(fpath, "rb") as f:
                file_bytes = f.read()

            print(f"[+] Ingesting '{fname}' ({size_mb:.2f} MB)...", end=" ", flush=True)
            doc_resp = await service.ingest_document(
                course_id=course.id,
                filename=fname,
                file_bytes=file_bytes,
            )

            if doc_resp.status == DocumentStatus.INDEXED:
                print(f"SUCCESS -> {doc_resp.chunk_count} chunks, {doc_resp.page_count} pages.")
                indexed += 1
            elif doc_resp.status == DocumentStatus.EMPTY:
                print("EMPTY -> No extractable text found.")
                skipped += 1
            else:
                print(f"{doc_resp.status} ({doc_resp.error_message})")
                skipped += 1

        except Exception as exc:
            print(f"FAILED -> {exc}")
            failed += 1

    print(f"\nResult for {course.code}: Indexed={indexed}, Skipped={skipped}, Failed={failed}")
    return indexed, skipped, failed


async def main():
    parser = argparse.ArgumentParser(
        description="Generalized Recall Course Knowledge Ingestion Tool"
    )
    parser.add_argument(
        "--course", "-c",
        type=str,
        help="Target course code (e.g. CS340, CS101, MATH201)",
    )
    parser.add_argument(
        "--title", "-t",
        type=str,
        help="Optional human-readable course title when creating a new course",
    )
    parser.add_argument(
        "--desc",
        type=str,
        help="Optional course description",
    )
    parser.add_argument(
        "--dir", "-d",
        type=str,
        help="Directory containing documents to ingest for the specified course",
    )
    parser.add_argument(
        "--scan-dir",
        type=str,
        help="Root directory where each subfolder is a course code (e.g. ./knowledge)",
    )
    parser.add_argument(
        "--max-size-mb",
        type=float,
        default=30.0,
        help="Max file size in megabytes before skipping (default: 30.0 MB)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect files and estimate without modifying the database",
    )
    parser.add_argument(
        "--test-query",
        type=str,
        help="Optional test query to run vector retrieval after ingestion",
    )

    args = parser.parse_args()

    if not args.course and not args.scan_dir:
        parser.print_help()
        print("\nERROR: Please specify either --course and --dir, or --scan-dir.")
        sys.exit(1)

    print("=" * 65)
    print("RECALL GENERALIZED COURSE KNOWLEDGE INGESTION ENGINE")
    print("=" * 65)

    async with AsyncSessionLocal() as session:
        # Mode 1: Multi-course batch scan from root directory (e.g. ./knowledge)
        if args.scan_dir:
            scan_path = os.path.abspath(args.scan_dir)
            if not os.path.isdir(scan_path):
                print(f"ERROR: Scan directory '{scan_path}' does not exist.")
                sys.exit(1)

            subdirs = [
                d for d in os.listdir(scan_path)
                if os.path.isdir(os.path.join(scan_path, d))
            ]
            print(f"Discovered {len(subdirs)} course directories in '{scan_path}': {subdirs}")

            for ccode in subdirs:
                cpath = os.path.join(scan_path, ccode)
                files = discover_files(cpath, recursive=True)
                if not files:
                    print(f"[*] No supported files found in '{ccode}', skipping.")
                    continue

                course = await get_or_create_course(session, ccode)
                await ingest_files_for_course(
                    session=session,
                    course=course,
                    files=files,
                    max_size_mb=args.max_size_mb,
                    dry_run=args.dry_run,
                )

        # Mode 2: Targeted single course ingestion
        elif args.course and args.dir:
            target_dir = os.path.abspath(args.dir)
            if not os.path.isdir(target_dir):
                print(f"ERROR: Directory '{target_dir}' does not exist.")
                sys.exit(1)

            files = discover_files(target_dir, recursive=True)
            print(f"Discovered {len(files)} files in '{target_dir}'.")

            course = await get_or_create_course(
                session=session,
                course_code=args.course,
                title=args.title,
                description=args.desc,
            )
            await ingest_files_for_course(
                session=session,
                course=course,
                files=files,
                max_size_mb=args.max_size_mb,
                dry_run=args.dry_run,
            )

            # Optional test query
            if args.test_query and not args.dry_run:
                service = KnowledgeService(session)
                print(f"\n[VERIFY] Testing vector retrieval for '{args.test_query}':")
                retrieval = await service.retrieve_knowledge(
                    course_id=course.id,
                    query=args.test_query,
                    top_k=3,
                )
                print(f"Matches found: {len(retrieval.matches)}")
                for i, m in enumerate(retrieval.matches, 1):
                    print(f"  #{i}: [{m.document_filename}, p.{m.page_number}] Score: {m.similarity_score:.3f}")

    print("\n" + "=" * 65)
    print("INGESTION PROCESS COMPLETE")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())
