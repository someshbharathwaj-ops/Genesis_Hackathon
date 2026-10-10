"""Unit tests for DBMSDeterministicGrader."""

import pytest

from app.modules.adaptive_learning.dbms_grader import DBMSDeterministicGrader


@pytest.mark.unit
def test_grade_attribute_closure_exact_and_deductions() -> None:
    answer_key = {"closure": "A, B, C, D"}
    rubric = {"type": "attribute_closure", "points": 1.0}

    # Correct submission
    res_correct = DBMSDeterministicGrader.grade(
        question_type="expression",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"closure": "A, B, C, D"},
        max_score=1.0,
    )
    assert res_correct.is_correct is True
    assert res_correct.score_achieved == 1.0
    assert len(res_correct.provenance["deductions"]) == 0

    # Incomplete submission (missing D)
    res_incomplete = DBMSDeterministicGrader.grade(
        question_type="expression",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"closure": "A, B, C"},
        max_score=1.0,
    )
    assert res_incomplete.is_correct is False
    assert res_incomplete.score_achieved == 0.0
    assert any(
        d["reason"] == "Missing attributes in closure"
        for d in res_incomplete.provenance["deductions"]
    )


@pytest.mark.unit
def test_grade_candidate_keys() -> None:
    answer_key = {"candidate_keys": ["AC", "BC", "CD"]}
    rubric = {"type": "candidate_keys", "points": 2.0}

    # Order-independent correct submission
    res = DBMSDeterministicGrader.grade(
        question_type="expression",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"candidate_keys": ["CD", "CA", "CB"]},
        max_score=2.0,
    )
    assert res.is_correct is True
    assert res.score_achieved == 2.0

    # Extra non-minimal key
    res_extra = DBMSDeterministicGrader.grade(
        question_type="expression",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"candidate_keys": ["AC", "BC", "CD", "ABC"]},
        max_score=2.0,
    )
    assert res_extra.is_correct is False
    assert any(
        "Spurious or non-minimal" in d["reason"]
        for d in res_extra.provenance["deductions"]
    )


@pytest.mark.unit
def test_grade_minimal_cover() -> None:
    answer_key = {"fds": ["A -> B", "B -> C"]}
    rubric = {"type": "minimal_cover", "points": 3.0}

    # Valid equivalent minimal cover
    res = DBMSDeterministicGrader.grade(
        question_type="minimal_cover",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"fds": ["A -> B", "B -> C"]},
        max_score=3.0,
    )
    assert res.is_correct is True
    assert res.score_achieved == 3.0

    # Redundant FD included
    res_redundant = DBMSDeterministicGrader.grade(
        question_type="minimal_cover",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"fds": ["A -> B", "B -> C", "A -> C"]},
        max_score=3.0,
    )
    assert res_redundant.is_correct is False


@pytest.mark.unit
def test_grade_decomposition_lossless_bcnf() -> None:
    answer_key = {
        "relation_attrs": "A, B, C",
        "fds": ["A -> B", "B -> C"],
    }
    rubric = {
        "type": "decomposition",
        "target_normal_form": "BCNF",
        "require_dependency_preservation": True,
        "points": 2.0,
    }

    # Correct BCNF decomposition: R1(B, C), R2(A, B)
    res = DBMSDeterministicGrader.grade(
        question_type="normalization_decomposition",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"relations": ["BC", "AB"]},
        max_score=2.0,
    )
    assert res.is_correct is True
    assert res.score_achieved == 2.0

    # Lossy decomposition: R1(A, C), R2(B, C)
    res_lossy = DBMSDeterministicGrader.grade(
        question_type="normalization_decomposition",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"relations": ["AC", "BC"]},
        max_score=2.0,
    )
    assert res_lossy.is_correct is False
    assert any("lossless-join" in d["reason"] for d in res_lossy.provenance["deductions"])


@pytest.mark.unit
def test_grade_hint_penalty_and_repetition_discount() -> None:
    answer_key = {"value": "B"}
    rubric = {"type": "multiple_choice", "points": 1.0}

    # Correct with 1 hint
    res_hint1 = DBMSDeterministicGrader.grade(
        question_type="multiple_choice",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"value": "B"},
        max_score=1.0,
        is_hint_assisted=True,
        hint_count=1,
        prior_attempt_count=0,
    )
    assert res_hint1.is_correct is True
    assert res_hint1.score_achieved == 0.75  # 25% discount
    assert res_hint1.provenance["is_hint_assisted"] is True
    assert res_hint1.provenance["repetition_discount_applied"] is False

    # Repeat attempt
    res_repeat = DBMSDeterministicGrader.grade(
        question_type="multiple_choice",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={"value": "B"},
        max_score=1.0,
        is_hint_assisted=False,
        hint_count=0,
        prior_attempt_count=1,
    )
    assert res_repeat.is_correct is True
    assert res_repeat.score_achieved == 1.0
    assert res_repeat.provenance["repetition_discount_applied"] is True


@pytest.mark.unit
def test_grade_malformed_submitted_answer() -> None:
    answer_key = {"candidate_keys": ["A"]}
    rubric = {"type": "candidate_keys", "points": 1.0}

    # Empty dictionary submitted
    res_empty = DBMSDeterministicGrader.grade(
        question_type="expression",
        answer_key=answer_key,
        rubric=rubric,
        submitted_answer={},
        max_score=1.0,
    )
    assert res_empty.is_correct is False
    assert res_empty.score_achieved == 0.0

    # Malformed minimal cover syntax (missing arrow)
    mc_key = {"fds": ["A -> B"]}
    mc_rubric = {"type": "minimal_cover", "points": 1.0}
    res_malformed_fd = DBMSDeterministicGrader.grade(
        question_type="minimal_cover",
        answer_key=mc_key,
        rubric=mc_rubric,
        submitted_answer={"fds": ["A - B", "INVALID_FD"]},
        max_score=1.0,
    )
    assert res_malformed_fd.is_correct is False
    assert any("Malformed" in d["reason"] for d in res_malformed_fd.provenance["deductions"])

    # Malformed decomposition (empty list / invalid relation)
    decomp_key = {"relation_attrs": "A, B", "fds": ["A -> B"]}
    decomp_rubric = {"type": "decomposition", "points": 1.0}
    res_malformed_decomp = DBMSDeterministicGrader.grade(
        question_type="normalization_decomposition",
        answer_key=decomp_key,
        rubric=decomp_rubric,
        submitted_answer={"relations": []},
        max_score=1.0,
    )
    assert res_malformed_decomp.is_correct is False

    # Unsupported rubric type fallback to exact match
    unknown_rubric = {"type": "unsupported_unknown_rubric", "points": 1.0}
    res_unknown = DBMSDeterministicGrader.grade(
        question_type="custom_type",
        answer_key={"value": "TRUE"},
        rubric=unknown_rubric,
        submitted_answer={"value": "TRUE"},
        max_score=1.0,
    )
    assert res_unknown.is_correct is True
    assert res_unknown.score_achieved == 1.0
