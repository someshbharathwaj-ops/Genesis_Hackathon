"""Unit tests verifying RFC 7807 error schema and domain exceptions."""

import pytest

from app.core.errors import (
    AssessmentLockoutError,
    IdempotencyConflictError,
    InsufficientGroundingError,
    ProblemDetails,
    ResourceNotFoundError,
)


@pytest.mark.unit
def test_problem_details_defaults() -> None:
    problem = ProblemDetails(
        title="Test Error",
        status=400,
        detail="Test detail",
    )
    dumped = problem.model_dump()
    assert dumped["status"] == 400
    assert dumped["title"] == "Test Error"
    assert "timestamp" in dumped
    assert dumped["code"] == "INTERNAL_ERROR"


@pytest.mark.unit
def test_resource_not_found_exception() -> None:
    exc = ResourceNotFoundError("Question", "q-101")
    assert exc.status_code == 404
    assert exc.code == "RESOURCE_NOT_FOUND"
    assert "q-101" in exc.detail


@pytest.mark.unit
def test_assessment_lockout_exception() -> None:
    exc = AssessmentLockoutError("student-42", "quiz-99")
    assert exc.status_code == 403
    assert exc.code == "ASSESSMENT_LOCKOUT"
    assert "student-42" in exc.detail
    assert "quiz-99" in exc.detail


@pytest.mark.unit
def test_idempotency_conflict_exception() -> None:
    exc = IdempotencyConflictError("idem-abc-123")
    assert exc.status_code == 409
    assert exc.code == "IDEMPOTENCY_CONFLICT"
    assert "idem-abc-123" in exc.detail


@pytest.mark.unit
def test_insufficient_grounding_exception() -> None:
    exc = InsufficientGroundingError("What is 5NF?")
    assert exc.status_code == 422
    assert exc.code == "UNVERIFIED_EVIDENCE"
    assert "What is 5NF?" in exc.detail
