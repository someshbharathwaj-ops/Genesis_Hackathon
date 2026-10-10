"""Unit tests for repository methods and idempotency service."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import IdempotencyConflictError
from app.models.identity import Course, User, UserRole
from app.repositories.course_repo import CourseRepository
from app.repositories.user_repo import UserRepository
from app.services.idempotency_service import IdempotencyService, compute_payload_hash


@pytest.mark.unit
async def test_user_repository_crud(test_db_session: AsyncSession) -> None:
    repo = UserRepository(test_db_session)
    user = User(
        email="test_repo@recall.edu",
        full_name="Test Repo User",
        role=UserRole.STUDENT,
    )
    created = await repo.create(user)
    assert created.id is not None

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.email == "test_repo@recall.edu"

    by_email = await repo.get_by_email("test_repo@recall.edu")
    assert by_email is not None
    assert by_email.id == created.id

    all_users = await repo.list_all()
    assert len(all_users) >= 1

    await repo.delete(created)
    deleted = await repo.get_by_id(created.id)
    assert deleted is None


@pytest.mark.unit
async def test_course_repository_get_by_code(test_db_session: AsyncSession) -> None:
    repo = CourseRepository(test_db_session)
    course = Course(
        code="CS101",
        title="Intro to Computing",
        description="Foundational principles",
    )
    await repo.create(course)

    by_code = await repo.get_by_code("CS101")
    assert by_code is not None
    assert by_code.title == "Intro to Computing"

    missing = await repo.get_by_code("NONEXISTENT")
    assert missing is None


@pytest.mark.unit
async def test_idempotency_service_record_and_conflict(test_db_session: AsyncSession) -> None:
    service = IdempotencyService(test_db_session)
    idem_key = "key-idem-999"
    payload = {"data": "initial"}
    resp_body = {"status": "ok"}

    # Initially none
    res = await service.get_existing_result(idem_key, payload)
    assert res is None

    # Record
    await service.record_response(
        idempotency_key=idem_key,
        request_path="/api/v1/test",
        request_payload=payload,
        status_code=200,
        response_body=resp_body,
    )

    # Replay matching payload
    code, cached = await service.get_existing_result(idem_key, payload) or (None, None)
    assert code == 200
    assert cached == resp_body

    # Payload conflict raises exception
    with pytest.raises(IdempotencyConflictError):
        await service.get_existing_result(idem_key, {"data": "different"})


@pytest.mark.unit
def test_compute_payload_hash_bytes_and_string() -> None:
    b_hash = compute_payload_hash(b"hello world")
    assert len(b_hash) == 64

    s_hash = compute_payload_hash("hello world")
    assert len(s_hash) == 64
