"""Generalized Course Seeder.

Dynamically seeds curriculum, topics, learning objectives, student enrollments,
and knowledge base documents for any course (DBMS, OS, or any new custom course).
"""

from pathlib import Path
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.curriculum import LearningObjective, Topic
from app.models.document import CourseDocument
from app.models.identity import Course, CourseEnrollment, User, UserRole
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.user_repo import EnrollmentRepository, UserRepository


async def seed_course_by_code(
    session: AsyncSession,
    course_code: str,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """Dynamically seed curriculum and resources for any given course code."""
    code_upper = course_code.strip().upper()

    # Route to specialized course seeds if available
    if code_upper in ("DBMS", "CS340"):
        from app.seeds.seed_dbms_questions import seed_dbms_curriculum_and_questions

        return await seed_dbms_curriculum_and_questions(session)

    if code_upper in ("OS", "CS301"):
        from app.seeds.seed_os_questions import seed_os_curriculum_and_questions

        return await seed_os_curriculum_and_questions(session)

    # General / Custom Course Seeder
    user_repo = UserRepository(session)
    course_repo = CourseRepository(session)
    enroll_repo = EnrollmentRepository(session)
    topic_repo = TopicRepository(session)
    lo_repo = LearningObjectiveRepository(session)

    # 1. Lead Instructor
    instructor = await user_repo.get_by_email("instructor.general@recall.edu")
    if not instructor:
        instructor = User(
            email="instructor.general@recall.edu",
            full_name="Prof. Academic Director",
            role=UserRole.INSTRUCTOR,
        )
        await user_repo.create(instructor)

    # 2. Course
    course = await course_repo.get_by_code(code_upper)
    if not course:
        course = Course(
            code=code_upper,
            title=title or f"{code_upper} Fundamentals",
            description=description or f"Authoritative curriculum, practice questions, and grounded AI tutor for {code_upper}.",
            instructor_id=instructor.id,
        )
        await course_repo.create(course)

    # 3. Student Ada Enrollment
    student = await user_repo.get_by_email("student.ada@recall.edu")
    if student:
        existing_enrollment = await enroll_repo.get_enrollment(student.id, course.id)
        if not existing_enrollment:
            enrollment = CourseEnrollment(
                user_id=student.id,
                course_id=course.id,
                is_active=True,
            )
            await enroll_repo.create(enrollment)

    # 4. Core Topic
    topics = await topic_repo.list_by_course(course.id)
    topic_code = f"{code_upper}_CORE"
    topic = next((t for t in topics if t.code == topic_code), None)
    if not topic:
        topic = Topic(
            course_id=course.id,
            code=topic_code,
            title=f"{code_upper} Core Principles",
            description=f"Core concepts, theoretical foundations, and practical techniques in {code_upper}.",
            order_index=1,
            objectives=[],
        )
        await topic_repo.create(topic)

    # 5. Core Learning Objectives
    lo_defs = [
        (
            f"LO_{code_upper}_FOUNDATIONS",
            f"{code_upper} Foundations & Terminology",
            f"Core vocabulary, architectural components, and foundational axioms of {code_upper}.",
            1,
            [],
        ),
        (
            f"LO_{code_upper}_APPLICATION",
            f"{code_upper} Applied Analysis & Problem Solving",
            f"Practical problem solving, algorithmic procedures, and evaluation in {code_upper}.",
            2,
            [f"LO_{code_upper}_FOUNDATIONS"],
        ),
    ]

    existing_los = await lo_repo.list_by_topic(topic.id)
    lo_map: dict[str, LearningObjective] = {lo.code: lo for lo in existing_los}

    for lo_code, lo_title, lo_desc, order, prereq_codes in lo_defs:
        if lo_code not in lo_map:
            prereq_ids = [lo_map[c].id for c in prereq_codes if c in lo_map]
            lo = LearningObjective(
                topic_id=topic.id,
                code=lo_code,
                title=lo_title,
                description=lo_desc,
                order_index=order,
                prerequisite_objective_ids=prereq_ids,
            )
            await lo_repo.create(lo)
            lo_map[lo_code] = lo

    # 6. Auto-Ingest Existing Documents (if knowledge/ folder exists)
    ingested_count = 0
    try:
        from app.services.knowledge_service import KnowledgeService

        base_knowledge = Path(__file__).resolve().parents[3] / "knowledge"
        candidate_dirs = [
            base_knowledge / code_upper,
            base_knowledge / course_code,
            Path(__file__).resolve().parents[3] / code_upper / "theory",
        ]
        ks = KnowledgeService(session)
        for k_dir in candidate_dirs:
            if k_dir.exists():
                for ext in ("*.md", "*.txt", "*.pdf"):
                    for doc_path in k_dir.glob(ext):
                        stmt = select(CourseDocument).where(
                            CourseDocument.course_id == course.id,
                            CourseDocument.filename == doc_path.name,
                        )
                        res = await session.execute(stmt)
                        if not res.scalar_one_or_none():
                            mime = (
                                "text/markdown"
                                if doc_path.suffix == ".md"
                                else "application/pdf"
                                if doc_path.suffix == ".pdf"
                                else "text/plain"
                            )
                            await ks.ingest_document(
                                course_id=course.id,
                                filename=doc_path.name,
                                file_bytes=doc_path.read_bytes(),
                                mime_type=mime,
                            )
                            ingested_count += 1
    except Exception:
        pass

    return {
        "status": "success",
        "course_id": course.id,
        "course_code": course.code,
        "course_title": course.title,
        "topic_id": topic.id,
        "objectives_count": len(lo_map),
        "new_questions_seeded": 0,
        "documents_ingested": ingested_count,
    }
