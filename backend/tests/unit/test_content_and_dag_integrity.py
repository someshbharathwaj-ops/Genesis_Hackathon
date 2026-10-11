"""Automated tests for curriculum DAG integrity, question schemas, and knowledge linking."""

from pathlib import Path
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import LearningObjective, Topic
from app.models.identity import Course
from app.models.question import Question, QuestionVersion, QuestionType, DifficultyLevel
from app.seeds.seed_all_comprehensive_curriculum import seed_comprehensive_curriculum
from scripts.validate_and_ingest_content import ContentDAGValidator


@pytest.mark.unit
async def test_learning_dag_acyclicity_and_topological_validity(test_db_session: AsyncSession) -> None:
    """Verify that every course learning DAG is acyclic (0 cycles) and has valid roots."""
    # Seed full curriculum
    await seed_comprehensive_curriculum(test_db_session)

    validator = ContentDAGValidator(Path(__file__).resolve().parent.parent.parent.parent)

    courses = (await test_db_session.execute(select(Course))).scalars().all()
    assert len(courses) >= 3, "All registered courses must be present in the database."

    for course in courses:
        los = (
            await test_db_session.execute(
                select(LearningObjective)
                .join(Topic, LearningObjective.topic_id == Topic.id)
                .where(Topic.course_id == course.id)
            )
        ).scalars().all()

        assert len(los) > 0, f"Course {course.code} must have learning objectives."

        # Validate DAG
        dag_result = validator.validate_course_dag(course.code, los)
        assert dag_result["is_acyclic"], f"Course {course.code} DAG must be acyclic! Found {dag_result['cycle_count']} cycles."
        assert dag_result["cycle_count"] == 0, f"Course {course.code} has cycles."
        assert dag_result["roots_count"] >= 1, f"Course {course.code} must have at least one root objective."
        assert len(dag_result["topological_order_codes"]) == len(los), "All objectives must appear in topological ordering."


@pytest.mark.unit
async def test_question_schema_integrity_and_provenance(test_db_session: AsyncSession) -> None:
    """Verify that all questions have valid type, rubric, answer key, difficulty, and max_score."""
    await seed_comprehensive_curriculum(test_db_session)

    questions = (await test_db_session.execute(select(Question))).scalars().all()
    assert len(questions) >= 30, "Expanded question bank must have at least 30 questions across courses."

    for q in questions:
        assert q.title, "Question must have a non-empty title."
        assert isinstance(q.question_type, QuestionType), f"Question {q.id} has invalid question type."

        # Verify QuestionVersion
        versions = (
            await test_db_session.execute(
                select(QuestionVersion).where(QuestionVersion.question_id == q.id)
            )
        ).scalars().all()
        assert len(versions) >= 1, f"Question {q.id} must have at least one version."

        v = versions[0]
        assert v.prompt and len(v.prompt) > 10, f"Version for {q.id} must have a detailed prompt."
        assert v.max_score > 0, f"Version for {q.id} must have max_score > 0."
        assert isinstance(v.difficulty, DifficultyLevel), f"Version for {q.id} has invalid difficulty."
        assert v.answer_key and "value" in v.answer_key, f"Version for {q.id} must have valid answer_key."
        assert v.rubric and "type" in v.rubric, f"Version for {q.id} must have rubric specification."
        assert v.provenance_hash and len(v.provenance_hash) == 64, f"Version for {q.id} must have valid SHA-256 provenance hash."


@pytest.mark.unit
async def test_knowledge_base_files_exist_and_grounded(test_db_session: AsyncSession) -> None:
    """Verify that focused knowledge markdown files exist on disk for all registered courses."""
    workspace_root = Path(__file__).resolve().parent.parent.parent.parent
    knowledge_dir = workspace_root / "knowledge"

    courses = ["CS340", "CS301", "CS305"]
    for code in courses:
        course_dir = knowledge_dir / code
        assert course_dir.exists(), f"Knowledge directory for {code} must exist."
        files = list(course_dir.glob("*.md"))
        assert len(files) >= 3, f"Course {code} must have at least 3 focused knowledge markdown files."

        # Verify files are non-empty and have section headings
        for f in files:
            content = f.read_text(encoding="utf-8")
            assert len(content) > 500, f"Knowledge file {f.name} in {code} is too short."
            assert f"Course ID:** `{code}`" in content or code in content, f"Knowledge file {f.name} must reference course {code}."
