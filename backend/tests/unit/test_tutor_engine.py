"""Unit tests for TutorService orchestration, assessment lockout, and state immutability."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AssessmentLockoutError, ResourceNotFoundError
from app.models.attempt import AssessmentContext, Attempt, AttemptStatus
from app.models.document import CourseDocument, DocumentChunk, DocumentStatus
from app.models.identity import Course, User, UserRole
from app.modules.ai_engine.model_provider import DeterministicMockLanguageModelProvider
from app.repositories.attempt_repo import AttemptRepository
from app.services.tutor_service import TutorService


@pytest.mark.unit
async def test_tutor_service_grounded_answer(
    test_db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Setup test course and student
    course = Course(id="c_dbms", code="CS340", title="Database Systems")
    student = User(
        id="s_alice",
        email="alice@test.edu",
        full_name="Alice Student",
        role=UserRole.STUDENT,
    )
    test_db_session.add_all([course, student])

    # Setup document and chunk
    doc = CourseDocument(
        id="d1",
        course_id="c_dbms",
        filename="dbms_lec1.pdf",
        content_hash="hash1",
        mime_type="application/pdf",
        file_size_bytes=1000,
        page_count=1,
        status=DocumentStatus.INDEXED,
    )
    mock_prov = DeterministicMockLanguageModelProvider()
    vec = [0.1] * 128
    chunk = DocumentChunk(
        id="chk1",
        document_id="d1",
        course_id="c_dbms",
        chunk_index=0,
        page_number=1,
        content="Armstrong's Axioms consist of Reflexivity, Augmentation, and Transitivity.",
        token_count=10,
        embedding=vec,
        metadata_attributes={"source_filename": "dbms_lec1.pdf"},
    )
    test_db_session.add_all([doc, chunk])
    await test_db_session.commit()

    service = TutorService(session=test_db_session, model_provider=mock_prov)

    # Monkeypatch embedding provider to return matching vector
    async def mock_embed_query(query: str) -> list[float]:
        return [0.1] * 128

    monkeypatch.setattr(
        service.knowledge_service.embedding_provider,
        "embed_query",
        mock_embed_query,
    )

    resp = await service.ask_tutor(
        course_id="c_dbms",
        student_id="s_alice",
        query="What are Armstrong's axioms?",
    )

    assert not resp.abstention_recommended
    assert resp.retrieved_chunks_count > 0
    assert len(resp.citations) > 0
    assert "[Lecture: dbms_lec1.pdf, Page 1]" in resp.citations[0]
    assert "Armstrong" in resp.answer


@pytest.mark.unit
async def test_tutor_service_abstention_on_empty_retrieval(test_db_session: AsyncSession) -> None:
    course = Course(id="c_empty", code="EMPTY101", title="Empty Course")
    student = User(id="s_bob", email="bob@test.edu", full_name="Bob Student", role=UserRole.STUDENT)
    test_db_session.add_all([course, student])
    await test_db_session.commit()

    service = TutorService(session=test_db_session)
    resp = await service.ask_tutor(
        course_id="c_empty",
        student_id="s_bob",
        query="Explain Relational Calculus",
    )

    assert resp.abstention_recommended
    assert resp.retrieved_chunks_count == 0
    assert len(resp.citations) == 0
    assert "abstaining" in resp.answer.lower()


@pytest.mark.unit
async def test_tutor_service_assessment_lockout(test_db_session: AsyncSession) -> None:
    from app.models.curriculum import LearningObjective, Topic
    from app.models.question import (
        DifficultyLevel,
        Question,
        QuestionType,
        QuestionVersion,
        VerificationStatus,
    )

    course = Course(id="c_lock", code="CS341", title="Database Systems Locked")
    student = User(
        id="s_charlie",
        email="charlie@test.edu",
        full_name="Charlie",
        role=UserRole.STUDENT,
    )
    topic = Topic(id="top_lock", course_id="c_lock", code="T1", title="Topic 1", order_index=1)
    lo = LearningObjective(
        id="lo_lock",
        topic_id="top_lock",
        code="LO1",
        title="LO 1",
        description="desc",
        order_index=1,
        prerequisite_objective_ids=[],
        metadata_attributes={},
    )
    q = Question(
        id="q1",
        objective_id="lo_lock",
        title="Q1",
        question_type=QuestionType.MULTIPLE_CHOICE,
        is_active=True,
    )
    qv = QuestionVersion(
        id="qv1",
        question_id="q1",
        version_number=1,
        prompt="prompt",
        difficulty=DifficultyLevel.INTRODUCTORY,
        max_score=1.0,
        options=[],
        answer_key={},
        rubric={},
        explanation="",
        verification_status=VerificationStatus.VERIFIED,
        provenance_hash="prov",
    )
    test_db_session.add_all([course, student, topic, lo, q, qv])
    await test_db_session.commit()

    # Create active in_progress attempt for charlie
    attempt = Attempt(
        id="att_active",
        idempotency_key="key_charlie_1",
        student_id="s_charlie",
        question_id="q1",
        question_version_id="qv1",
        assessment_context=AssessmentContext.DIAGNOSTIC,
        submitted_answer={"answer": "in progress"},
        is_hint_assisted=False,
        hint_count=0,
        time_spent_ms=5000,
        status=AttemptStatus.IN_PROGRESS,
        is_correct=False,
        score_achieved=0.0,
        max_possible_score=1.0,
        grading_provenance={},
    )
    test_db_session.add(attempt)
    await test_db_session.commit()

    service = TutorService(session=test_db_session)
    with pytest.raises(AssessmentLockoutError) as exc_info:
        await service.ask_tutor(
            course_id="c_lock",
            student_id="s_charlie",
            query="Can you give me the answer for question 1?",
        )

    assert exc_info.value.status_code == 403
    assert "lockout" in exc_info.value.title.lower()


@pytest.mark.unit
async def test_tutor_service_immutability_guarantee(test_db_session: AsyncSession) -> None:
    """Verify that Tutor queries never mutate attempts, grades, or mastery records."""
    course = Course(id="c_imm", code="IMM101", title="Immutable Course")
    student = User(id="s_dave", email="dave@test.edu", full_name="Dave", role=UserRole.STUDENT)
    test_db_session.add_all([course, student])
    await test_db_session.commit()

    attempt_repo = AttemptRepository(test_db_session)
    attempts_before = await attempt_repo.list_student_attempts("s_dave")

    service = TutorService(session=test_db_session)
    await service.ask_tutor(
        course_id="c_imm",
        student_id="s_dave",
        query="What is transaction isolation?",
    )

    attempts_after = await attempt_repo.list_student_attempts("s_dave")
    assert len(attempts_before) == len(attempts_after) == 0


@pytest.mark.unit
async def test_tutor_service_nonexistent_entities(test_db_session: AsyncSession) -> None:
    service = TutorService(session=test_db_session)

    with pytest.raises(ResourceNotFoundError) as exc_course:
        await service.ask_tutor(course_id="missing_c", student_id="missing_s", query="test")
    assert "Course" in exc_course.value.detail

    course = Course(id="c_exists", code="EX101", title="Existing Course")
    test_db_session.add(course)
    await test_db_session.commit()

    with pytest.raises(ResourceNotFoundError) as exc_user:
        await service.ask_tutor(course_id="c_exists", student_id="missing_s", query="test")
    assert "User" in exc_user.value.detail
