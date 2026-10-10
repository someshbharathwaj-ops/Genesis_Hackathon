"""Unit tests verifying Phase 1 models, provenance hashing, and data structures."""

import pytest

from app.models.attempt import AssessmentContext, AttemptStatus
from app.models.identity import UserRole
from app.models.question import DifficultyLevel, QuestionType, VerificationStatus
from app.repositories.question_repo import calculate_provenance_hash
from app.services.idempotency_service import compute_payload_hash


@pytest.mark.unit
def test_provenance_hash_is_deterministic() -> None:
    prompt = "Given relation R(A, B, C) with FDs {A -> B, B -> C}, find candidate keys."
    answer_key = {"value": ["A"], "reference": "Armstrong Axioms"}
    rubric = {"criterion": "Closure of A covers ABC", "points": 1.0}

    hash1 = calculate_provenance_hash(prompt, answer_key, rubric)
    hash2 = calculate_provenance_hash(prompt, answer_key, rubric)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length

    # Changed prompt produces different hash
    hash3 = calculate_provenance_hash(prompt + " Extra", answer_key, rubric)
    assert hash1 != hash3


@pytest.mark.unit
def test_payload_hash_key_order_invariance() -> None:
    payload_a = {"student_id": "s1", "value": "A", "time": 100}
    payload_b = {"time": 100, "value": "A", "student_id": "s1"}

    hash_a = compute_payload_hash(payload_a)
    hash_b = compute_payload_hash(payload_b)

    assert hash_a == hash_b


@pytest.mark.unit
def test_enums_contract_values() -> None:
    assert UserRole.STUDENT == "student"
    assert VerificationStatus.VERIFIED == "verified"
    assert QuestionType.MULTIPLE_CHOICE == "multiple_choice"
    assert DifficultyLevel.INTERMEDIATE == "intermediate"
    assert AttemptStatus.GRADED == "graded"
    assert AssessmentContext.DIAGNOSTIC == "diagnostic"
