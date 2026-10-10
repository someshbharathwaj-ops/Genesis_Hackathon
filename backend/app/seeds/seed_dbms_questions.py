"""Verified DBMS Question Bank Seeder for Functional Dependencies and Normalization.

Seeds:
- CS340 Database Management Systems course
- FD_NORM Topic
- 5 Granular Learning Objectives:
    1. LO_CLOSURE: Attribute Closure Computation
    2. LO_KEYS: Superkey and Candidate Key Derivation
    3. LO_MINIMAL_COVER: Minimal / Canonical Cover
    4. LO_NF_IDENTIFICATION: Normal Form Verification (2NF, 3NF, BCNF)
    5. LO_DECOMPOSITION: Lossless Join & Dependency Preservation
- 10+ rigorously verified, versioned questions with deterministic rubrics and provenance hashes.
"""

from typing import Any, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.curriculum import LearningObjective, Topic
from app.models.identity import Course, User, UserRole
from app.models.question import DifficultyLevel, Question, QuestionType, QuestionVersion, VerificationStatus
from app.repositories.course_repo import CourseRepository, LearningObjectiveRepository, TopicRepository
from app.repositories.question_repo import QuestionRepository, QuestionVersionRepository, calculate_provenance_hash
from app.repositories.user_repo import UserRepository

SEED_QUESTIONS_DATA: List[Dict[str, Any]] = [
    # --- LO_CLOSURE ---
    {
        "objective_code": "LO_CLOSURE",
        "title": "Attribute Closure on Transitive Chain",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": "Given relation schema R(A, B, C, D) and functional dependencies F = {A -> B, B -> C, C -> D}, compute the attribute closure {A}+.",
        "answer_key": {"closure": "A, B, C, D", "reference": "Armstrong Transitivity Axiom"},
        "rubric": {"type": "attribute_closure", "criterion": "Complete closure of {A}", "points": 1.0},
        "explanation": "A -> B adds B; B -> C adds C; C -> D adds D. Therefore, {A}+ = {A, B, C, D}.",
    },
    {
        "objective_code": "LO_CLOSURE",
        "title": "Attribute Closure with Composite LHS",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": "Given schema R(A, B, C, D, E) and F = {AB -> C, C -> D, D -> E}, compute the attribute closure {A, B}+.",
        "answer_key": {"closure": "A, B, C, D, E", "reference": "Composite Armstrong Closure"},
        "rubric": {"type": "attribute_closure", "criterion": "Complete closure of {A, B}", "points": 1.0},
        "explanation": "{A,B} implies C via AB -> C; C implies D; D implies E. Hence {A,B}+ = {A, B, C, D, E}.",
    },

    # --- LO_KEYS ---
    {
        "objective_code": "LO_KEYS",
        "title": "Single Candidate Key Identification",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": "Given relation schema R(A, B, C, D) with FDs {A -> B, BC -> D, D -> A}. Identify all candidate keys for R.",
        "answer_key": {"candidate_keys": ["AC", "BC", "CD"], "reference": "Minimal Superkeys Definition"},
        "rubric": {"type": "candidate_keys", "criterion": "All minimal candidate keys", "points": 1.0},
        "explanation": "C never appears on any RHS, so C must be in every candidate key. {A,C}+ = ABCD, {B,C}+ = ABCD, {C,D}+ = ABCD. Keys: AC, BC, CD.",
    },
    {
        "objective_code": "LO_KEYS",
        "title": "Candidate Keys with Disjoint Paths",
        "question_type": QuestionType.EXPRESSION,
        "difficulty": DifficultyLevel.ADVANCED,
        "max_score": 2.0,
        "prompt": "Given relation schema R(W, X, Y, Z) and F = {W -> X, X -> Y, Y -> Z, Z -> W}. List all candidate keys.",
        "answer_key": {"candidate_keys": ["W", "X", "Y", "Z"], "reference": "Cyclic Candidate Keys"},
        "rubric": {"type": "candidate_keys", "criterion": "Cyclic single-attribute candidate keys", "points": 2.0},
        "explanation": "Because of cyclic dependencies W -> X -> Y -> Z -> W, each single attribute closures to WXYZ. Candidate keys: {W}, {X}, {Y}, {Z}.",
    },

    # --- LO_MINIMAL_COVER ---
    {
        "objective_code": "LO_MINIMAL_COVER",
        "title": "Canonical Minimal Cover Derivation",
        "question_type": QuestionType.MINIMAL_COVER,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 2.0,
        "prompt": "Compute the minimal cover for relation R(A, B, C) with FDs F = {A -> B, A -> C, B -> C, AB -> C}.",
        "answer_key": {
            "fds": ["A -> B", "B -> C"],
            "reference": "Extraneous attribute & Redundancy elimination",
        },
        "rubric": {"type": "minimal_cover", "criterion": "Minimal cover with singleton RHS and no redundancy", "points": 2.0},
        "explanation": "AB -> C has extraneous B since A -> C. A -> C is redundant given A -> B and B -> C. Minimal cover: {A -> B, B -> C}.",
    },
    {
        "objective_code": "LO_MINIMAL_COVER",
        "title": "Minimal Cover with Extraneous LHS Attribute",
        "question_type": QuestionType.MINIMAL_COVER,
        "difficulty": DifficultyLevel.ADVANCED,
        "max_score": 2.0,
        "prompt": "Given F = {A -> B, B -> C, AB -> D}. Find the minimal cover.",
        "answer_key": {
            "fds": ["A -> B", "B -> C", "A -> D"],
            "reference": "Extraneous LHS Reduction",
        },
        "rubric": {"type": "minimal_cover", "criterion": "Reduced LHS minimal cover", "points": 2.0},
        "explanation": "In AB -> D, B is extraneous because {A}+ already contains B (since A -> B). Hence AB -> D reduces to A -> D. Minimal cover: {A -> B, B -> C, A -> D}.",
    },

    # --- LO_NF_IDENTIFICATION ---
    {
        "objective_code": "LO_NF_IDENTIFICATION",
        "title": "Identify 2NF Violation (Partial Dependency)",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTRODUCTORY,
        "max_score": 1.0,
        "prompt": "Given relation R(A, B, C, D) with candidate key AB and FDs {AB -> C, B -> D}. What is the highest normal form satisfied by R?",
        "options": [
            {"id": "1NF", "text": "1NF"},
            {"id": "2NF", "text": "2NF"},
            {"id": "3NF", "text": "3NF"},
            {"id": "BCNF", "text": "BCNF"},
        ],
        "answer_key": {"value": "1NF", "reference": "2NF Partial Dependency Violation"},
        "rubric": {"type": "multiple_choice", "criterion": "Correct Normal Form classification", "points": 1.0},
        "explanation": "D is non-prime and depends on B, which is a proper subset of candidate key AB. This violates 2NF. Highest normal form is 1NF.",
    },
    {
        "objective_code": "LO_NF_IDENTIFICATION",
        "title": "Identify 3NF vs BCNF Distinction",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": "Given relation R(A, B, C) with candidate keys AB and AC, and FDs {AB -> C, C -> B}. What is the highest normal form of R?",
        "options": [
            {"id": "1NF", "text": "1NF"},
            {"id": "2NF", "text": "2NF"},
            {"id": "3NF", "text": "3NF"},
            {"id": "BCNF", "text": "BCNF"},
        ],
        "answer_key": {"value": "3NF", "reference": "Codd 3NF Prime RHS Condition"},
        "rubric": {"type": "multiple_choice", "criterion": "3NF prime attribute rule", "points": 1.0},
        "explanation": "In C -> B, C is not a superkey (violating BCNF), but B is a prime attribute (part of candidate key AB), satisfying 3NF. Thus R is in 3NF.",
    },

    # --- LO_DECOMPOSITION ---
    {
        "objective_code": "LO_DECOMPOSITION",
        "title": "BCNF Lossless Join Decomposition",
        "question_type": QuestionType.NORMALIZATION_DECOMPOSITION,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 2.0,
        "prompt": "Decompose relation R(A, B, C) with FDs {A -> B, B -> C} into BCNF relations that guarantee a lossless join.",
        "answer_key": {
            "relation_attrs": "A, B, C",
            "fds": ["A -> B", "B -> C"],
            "reference": "BCNF Decomposition Theorem",
        },
        "rubric": {
            "type": "decomposition",
            "target_normal_form": "BCNF",
            "require_dependency_preservation": True,
            "criterion": "Lossless BCNF decomposition",
            "points": 2.0,
        },
        "explanation": "Candidate key is A. B -> C violates BCNF. Decomposing into R1(B, C) and R2(A, B): R1 ∩ R2 = {B}, and B -> BC in R1, ensuring lossless join. Both R1 and R2 are in BCNF.",
    },
    {
        "objective_code": "LO_DECOMPOSITION",
        "title": "Lossless Join Verification with Chase Theorem",
        "question_type": QuestionType.MULTIPLE_CHOICE,
        "difficulty": DifficultyLevel.INTERMEDIATE,
        "max_score": 1.0,
        "prompt": "Relation R(A, B, C, D) has FDs {A -> B, B -> C, C -> D}. Is decomposition D = {R1(A, B), R2(B, C), R3(C, D)} lossless?",
        "options": [
            {"id": "YES", "text": "Yes, it is lossless"},
            {"id": "NO", "text": "No, it is lossy"},
        ],
        "answer_key": {"value": "YES", "reference": "Chase Matrix Algorithm"},
        "rubric": {"type": "multiple_choice", "criterion": "Lossless decomposition assessment", "points": 1.0},
        "explanation": "R1 ∩ R2 = B and B -> BC. Then (R1 ∪ R2) ∩ R3 = C and C -> CD. By successive lossless joins, D is lossless.",
    },
]


async def seed_dbms_curriculum_and_questions(session: AsyncSession) -> Dict[str, Any]:
    """Idempotently seed the DBMS course, topic, objectives, and verified questions."""
    # 1. Instructor
    user_repo = UserRepository(session)
    instructor = await user_repo.get_by_email("instructor.dbms@recall.edu")
    if not instructor:
        instructor = User(
            email="instructor.dbms@recall.edu",
            full_name="Prof. E. F. Codd",
            role=UserRole.INSTRUCTOR,
        )
        await user_repo.create(instructor)

    # 2. Course
    course_repo = CourseRepository(session)
    course = await course_repo.get_by_code("CS340")
    if not course:
        course = Course(
            code="CS340",
            title="Database Management Systems",
            description="Relational data model, functional dependencies, and normal forms.",
            instructor_id=instructor.id,
        )
        await course_repo.create(course)

    # 3. Topic
    topic_repo = TopicRepository(session)
    topics = await topic_repo.list_by_course(course.id)
    topic = next((t for t in topics if t.code == "FD_NORM"), None)
    if not topic:
        topic = Topic(
            course_id=course.id,
            code="FD_NORM",
            title="Functional Dependencies & Normalization",
            description="Armstrong's axioms, minimal covers, 1NF-BCNF, and lossless decomposition.",
            order_index=1,
            objectives=[],
        )
        await topic_repo.create(topic)

    # 4. Objectives
    lo_repo = LearningObjectiveRepository(session)
    existing_los = await lo_repo.list_by_topic(topic.id)
    lo_map: Dict[str, LearningObjective] = {lo.code: lo for lo in existing_los}

    lo_definitions = [
        ("LO_CLOSURE", "Attribute Closure", "Compute attribute closures X+ via Armstrong axioms", 1, []),
        ("LO_KEYS", "Candidate Keys", "Determine superkeys and minimal candidate keys", 2, ["LO_CLOSURE"]),
        ("LO_MINIMAL_COVER", "Minimal Cover", "Synthesize minimal canonical covers of FDs", 3, ["LO_CLOSURE"]),
        ("LO_NF_IDENTIFICATION", "Normal Form Verification", "Diagnose 1NF, 2NF, 3NF, and BCNF violations", 4, ["LO_KEYS"]),
        ("LO_DECOMPOSITION", "Decomposition", "Validate lossless join and dependency preservation", 5, ["LO_NF_IDENTIFICATION"]),
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

    # 5. Verified Questions
    q_repo = QuestionRepository(session)
    v_repo = QuestionVersionRepository(session)
    seeded_count = 0

    for q_data in SEED_QUESTIONS_DATA:
        lo = lo_map[q_data["objective_code"]]
        # Check if question with this title already exists for this objective
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

        version = QuestionVersion(
            question_id=q.id,
            version_number=1,
            prompt=q_data["prompt"],
            difficulty=q_data["difficulty"],
            max_score=q_data["max_score"],
            options=q_data.get("options"),
            answer_key=q_data["answer_key"],
            rubric=q_data["rubric"],
            explanation=q_data["explanation"],
            verification_status=VerificationStatus.VERIFIED,
            verified_by="Prof. E. F. Codd",
            provenance_hash=prov_hash,
        )
        await v_repo.create(version)
        seeded_count += 1

    return {
        "status": "success",
        "course_id": course.id,
        "topic_id": topic.id,
        "objectives_count": len(lo_map),
        "new_questions_seeded": seeded_count,
        "total_catalog_questions": len(SEED_QUESTIONS_DATA),
    }
