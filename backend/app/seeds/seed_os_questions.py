"""Verified Operating Systems Question Bank and Curriculum Seeder.

Seeds:
- CS301 Operating Systems course
- Topics: Process Management, Concurrency, Scheduling, and Deadlocks
- Learning Objectives:
    1. LO_OS_PROCESS: Process Lifecycle & PCB
    2. LO_OS_SCHEDULING: CPU Scheduling (FCFS, SJF, Round Robin)
    3. LO_OS_SYNCHRONIZATION: Critical Section & Semaphores
    4. LO_OS_DEADLOCKS: Coffman Conditions & Deadlock
- Verified, versioned questions with rubrics, deterministic answer keys, and provenance hashes.
"""

from pathlib import Path
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.curriculum import LearningObjective, Topic
from app.models.document import CourseDocument
from app.models.identity import Course, CourseEnrollment, User, UserRole
from app.models.question import (
    DifficultyLevel,
    Question,
    QuestionType,
    QuestionVersion,
    VerificationStatus,
)
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.question_repo import (
    QuestionRepository,
    QuestionVersionRepository,
    calculate_provenance_hash,
)
from app.repositories.user_repo import EnrollmentRepository, UserRepository


SEED_OS_QUESTIONS_DATA: list[dict[str, Any]] = [
    # --- LO_OS_PROCESS ---
    {
        "objective_code": "LO_OS_PROCESS",
        "title": "Process State Transitions on I/O Block",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "When a running process initiates a disk read or system call that requires I/O completion, "
            "which state does the Operating System transition the process into?"
        ),
        "options": [
            {"id": "READY", "text": "READY"},
            {"id": "WAITING", "text": "WAITING / BLOCKED"},
            {"id": "TERMINATED", "text": "TERMINATED"},
            {"id": "NEW", "text": "NEW"},
        ],
        "answer_key": {"value": "WAITING", "reference": "Silberschatz Chapter 3 Process States"},
        "rubric": {
            "type": "multiple_choice",
            "criterion": "State must be WAITING / BLOCKED",
            "points": 1.0,
        },
        "explanation": (
            "A process requesting I/O cannot utilize the CPU until the I/O event completes. "
            "Therefore, the OS transitions it from RUNNING to WAITING (or BLOCKED)."
        ),
    },
    # --- LO_OS_SCHEDULING ---
    {
        "objective_code": "LO_OS_SCHEDULING",
        "title": "FCFS Convoy Effect Analysis",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "Which scheduling phenomenon occurs under FCFS when a long CPU-bound process holds the CPU, "
            "causing multiple short I/O-bound processes to wait in the ready queue?"
        ),
        "options": [
            {"id": "CONVOY", "text": "Convoy Effect"},
            {"id": "STARVATION", "text": "Starvation"},
            {"id": "INVERSION", "text": "Priority Inversion"},
            {"id": "THRASHING", "text": "Thrashing"},
        ],
        "answer_key": {"value": "CONVOY", "reference": "Silberschatz Chapter 5 CPU Scheduling"},
        "rubric": {
            "type": "multiple_choice",
            "criterion": "Phenomenon must be Convoy Effect",
            "points": 1.0,
        },
        "explanation": (
            "The convoy effect occurs when short processes wait behind a long process under FCFS scheduling, "
            "leading to lower CPU and device utilization."
        ),
    },
    {
        "objective_code": "LO_OS_SCHEDULING",
        "title": "Optimal Average Waiting Time Scheduling",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "Which CPU scheduling algorithm is mathematically proven to give the minimum average waiting time for a given set of processes?"
        ),
        "options": [
            {"id": "FCFS", "text": "First-Come, First-Served (FCFS)"},
            {"id": "SJF", "text": "Shortest-Job-First (SJF)"},
            {"id": "RR", "text": "Round Robin (RR)"},
            {"id": "PRIORITY", "text": "Priority Scheduling"},
        ],
        "answer_key": {"value": "SJF", "reference": "SJF Optimality Proof"},
        "rubric": {
            "type": "multiple_choice",
            "criterion": "Algorithm must be Shortest Job First",
            "points": 1.0,
        },
        "explanation": (
            "Shortest-Job-First (SJF) is provably optimal because scheduling a shorter process before a longer process "
            "decreases waiting time for the short process more than it increases waiting time for the long process."
        ),
    },
    # --- LO_OS_SYNCHRONIZATION ---
    {
        "objective_code": "LO_OS_SYNCHRONIZATION",
        "title": "Critical Section Problem Requirements",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": (
            "List the three fundamental requirements that any valid solution to the Critical Section Problem must satisfy."
        ),
        "answer_key": {
            "requirements": "Mutual Exclusion, Progress, Bounded Waiting",
            "reference": "Silberschatz Chapter 5 / Galvin",
        },
        "rubric": {
            "type": "string_set",
            "criterion": "Must include Mutual Exclusion, Progress, and Bounded Waiting",
            "points": 1.0,
        },
        "explanation": (
            "Any valid solution to the critical-section problem must satisfy: 1) Mutual Exclusion, 2) Progress, and 3) Bounded Waiting."
        ),
    },
    {
        "objective_code": "LO_OS_SYNCHRONIZATION",
        "title": "Counting Semaphore wait() Operation",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": (
            "In Dijkstra's classic semaphore specification, what does the atomic wait(S) or P(S) operation perform?"
        ),
        "options": [
            {"id": "DECR", "text": "Decrements S, blocks calling process if S < 0"},
            {"id": "INCR", "text": "Increments S, unblocks a waiting process"},
            {"id": "RESET", "text": "Resets S to 0 atomically"},
            {"id": "READ", "text": "Reads S without modifying it"},
        ],
        "answer_key": {"value": "DECR", "reference": "Dijkstra Semaphore Operations"},
        "rubric": {
            "type": "multiple_choice",
            "criterion": "wait decrements and blocks if negative",
            "points": 1.0,
        },
        "explanation": (
            "wait(S) decrements the semaphore value S. If the resulting value is negative, the calling process is blocked."
        ),
    },
    # --- LO_OS_DEADLOCKS ---
    {
        "objective_code": "LO_OS_DEADLOCKS",
        "title": "Coffman Conditions for Deadlock",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.ADVANCED,
        "max_score": 1.0,
        "prompt": (
            "Name the four necessary conditions (known as Coffman Conditions) that must hold simultaneously for a deadlock to arise."
        ),
        "answer_key": {
            "conditions": "Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait",
            "reference": "Coffman Conditions (1971)",
        },
        "rubric": {
            "type": "string_set",
            "criterion": "Must include Mutual Exclusion, Hold and Wait, No Preemption, Circular Wait",
            "points": 1.0,
        },
        "explanation": (
            "Deadlock can occur if and only if all four Coffman conditions hold: 1. Mutual Exclusion, 2. Hold and Wait, 3. No Preemption, 4. Circular Wait."
        ),
    },
]


async def seed_os_curriculum_and_questions(
    session: AsyncSession,
    comprehensive: bool = False,
) -> tuple[Course, list[Question]]:
    """Seed CS301 Operating Systems course, topics, learning objectives, and question bank."""
    user_repo = UserRepository(session)
    course_repo = CourseRepository(session)
    enroll_repo = EnrollmentRepository(session)
    topic_repo = TopicRepository(session)
    lo_repo = LearningObjectiveRepository(session)
    q_repo = QuestionRepository(session)
    v_repo = QuestionVersionRepository(session)

    # 1. Instructor
    instructor = await user_repo.get_by_email("instructor.os@recall.edu")
    if not instructor:
        instructor = User(
            email="instructor.os@recall.edu",
            full_name="Prof. Andrew Tanenbaum",
            role=UserRole.INSTRUCTOR,
        )
        await user_repo.create(instructor)

    # 2. Course CS301
    course = await course_repo.get_by_code("CS301")
    if not course:
        course = Course(
            code="CS301",
            title="Operating Systems & Concurrency",
            description="Process management, CPU scheduling, synchronization, deadlocks, and virtual memory.",
            instructor_id=instructor.id,
        )
        await course_repo.create(course)

    # 3. Student Enrollment
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

    # 4. Topic
    topics = await topic_repo.list_by_course(course.id)
    topic = next((t for t in topics if t.code == "OS_CORE"), None)
    if not topic:
        topic = Topic(
            course_id=course.id,
            code="OS_CORE",
            title="Process Management, Concurrency & Deadlocks",
            description="Processes, scheduling algorithms, critical sections, semaphores, and deadlocks.",
            order_index=1,
            objectives=[],
        )
        await topic_repo.create(topic)

    # 5. Objectives
    existing_los = await lo_repo.list_by_topic(topic.id)
    lo_map: dict[str, LearningObjective] = {lo.code: lo for lo in existing_los}

    lo_definitions = [
        ("LO_OS_PROCESS", "Process Lifecycle & PCB", "Understand process state machine and PCB", 1, []),
        ("LO_OS_SCHEDULING", "CPU Scheduling (FCFS, SJF, RR)", "Analyze FCFS, SJF, and Round Robin scheduling", 2, ["LO_OS_PROCESS"]),
        ("LO_OS_SYNCHRONIZATION", "Critical Section & Semaphores", "Understand race conditions, mutex, and semaphores", 3, ["LO_OS_PROCESS"]),
        ("LO_OS_DEADLOCKS", "Coffman Conditions & Deadlock", "Analyze Coffman conditions and deadlock prevention", 4, ["LO_OS_SYNCHRONIZATION"]),
    ]

    for code, title, desc, order, prereqs in lo_definitions:
        if code not in lo_map:
            lo = LearningObjective(
                topic_id=topic.id,
                code=code,
                title=title,
                description=desc,
                order_index=order,
                prerequisite_objective_ids=prereqs,
            )
            await lo_repo.create(lo)
            lo_map[code] = lo

    # 6. Questions
    created_questions: list[Question] = []
    for q_data in SEED_OS_QUESTIONS_DATA:
        lo = lo_map.get(q_data["objective_code"])
        if not lo:
            continue

        existing_qs = await q_repo.list_by_objective(lo.id)
        if any(eq.title == q_data["title"] for eq in existing_qs):
            continue

        q = Question(
            objective_id=lo.id,
            title=q_data["title"],
            question_type=q_data["question_type"],
            is_active=True,
        )
        await q_repo.create(q)

        prov_hash = calculate_provenance_hash(
            prompt=q_data["prompt"],
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
        )

        v = QuestionVersion(
            question_id=q.id,
            version_number=1,
            difficulty=q_data["difficulty"],
            max_score=q_data["max_score"],
            options=q_data.get("options"),
            prompt=q_data["prompt"],
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
            explanation=q_data["explanation"],
            verification_status=VerificationStatus.VERIFIED,
            verified_by="Prof. Andrew Tanenbaum",
            provenance_hash=prov_hash,
        )
        await v_repo.create(v)

        q.current_version_id = v.id
        created_questions.append(q)

    # 7. Auto-ingest authoritative documents if present
    try:
        from app.services.knowledge_service import KnowledgeService

        knowledge_dir = Path(__file__).resolve().parents[3] / "knowledge" / "CS301"
        if knowledge_dir.exists():
            ks = KnowledgeService(session)
            for md_file in knowledge_dir.glob("*.md"):
                stmt = select(CourseDocument).where(
                    CourseDocument.course_id == course.id,
                    CourseDocument.filename == md_file.name,
                )
                res = await session.execute(stmt)
                if not res.scalar_one_or_none():
                    file_bytes = md_file.read_bytes()
                    await ks.ingest_document(
                        course_id=course.id,
                        filename=md_file.name,
                        file_bytes=file_bytes,
                        mime_type="text/markdown",
                    )
    except Exception:
        pass

    if comprehensive:
        try:
            from app.seeds.seed_all_comprehensive_curriculum import seed_comprehensive_curriculum
            await seed_comprehensive_curriculum(session)
        except Exception:
            pass

    return {
        "status": "success",
        "course_id": course.id,
        "topic_id": topic.id,
        "objectives_count": len(lo_map),
        "new_questions_seeded": len(created_questions),
        "total_catalog_questions": len(SEED_OS_QUESTIONS_DATA),
    }
