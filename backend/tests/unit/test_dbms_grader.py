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
    assert any(d["reason"] == "Missing attributes in closure" for d in res_incomplete.provenance["deductions"])


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
    assert any("Spurious or non-minimal" in d["reason"] for d in res_extra.provenance["deductions"])


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
