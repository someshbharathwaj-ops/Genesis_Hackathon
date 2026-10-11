"""Unit tests for the Grounded Revisor Engine."""

from app.modules.ai_engine.revisor_engine import (
    GroundedAuditStatus,
    RevisorEngine,
)
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch


def _create_mock_match(
    chunk_id: str,
    doc_id: str,
    page_num: int,
    filename: str,
    content: str,
) -> RetrievalMatch:
    return RetrievalMatch(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_filename=filename,
        page_number=page_num,
        content=content,
        similarity_score=0.88,
        citation=f"[Lecture: {filename}, Page {page_num}]",
        metadata_attributes={},
    )


def test_revisor_assemble_prompt_bounds_and_citations() -> None:
    match1 = _create_mock_match(
        "c-1", "d-1", 1, "dbms_lec1.pdf", "Functional dependencies form the core of normalization."
    )
    match2 = _create_mock_match(
        "c-2",
        "d-1",
        2,
        "dbms_lec1.pdf",
        "Armstrong's axioms are reflexivity, augmentation, transitivity.",
    )

    prompt = RevisorEngine.assemble_prompt(
        candidate_text="Armstrong axioms are reflexivity and augmentation.",
        query_or_topic="Functional dependencies",
        matches=[match1, match2],
        max_context_chars=1000,
    )

    assert len(prompt.citations) == 2
    assert "[Lecture: dbms_lec1.pdf, Page 1]" in prompt.citations
    assert "[Lecture: dbms_lec1.pdf, Page 2]" in prompt.citations
    assert prompt.truncated is False
    assert "CANDIDATE TEXT UNDER REVIEW:" in prompt.user_prompt


def test_revisor_parse_verified_grounded() -> None:
    citations = ["[Lecture: dbms.pdf, Page 3]"]
    model_output = (
        "STATUS: VERIFIED_GROUNDED\n"
        "SUMMARY: The explanation strictly follows the lecture notes.\n"
        "VERIFIED POINTS:\n"
        "- Reflexivity rule is accurate.\n"
        "- BCNF definition matches slide 3 [Lecture: dbms.pdf, Page 3].\n"
        "FLAGGED ISSUES:\n"
        "None\n"
        "SUGGESTED REVISION:\n"
        "None needed\n"
    )

    result = RevisorEngine.parse_model_output(model_output, citations)
    assert result.audit_status == GroundedAuditStatus.VERIFIED_GROUNDED
    assert result.is_approved is True
    assert len(result.verified_points) == 2
    assert len(result.flagged_issues) == 0
    assert result.abstention_recommended is False


def test_revisor_parse_ungrounded_claims() -> None:
    citations = ["[Lecture: dbms.pdf, Page 3]"]
    model_output = (
        "STATUS: UNGROUNDED_CLAIM_DETECTED\n"
        "SUMMARY: Candidate introduces unverified claims not present in syllabus.\n"
        "VERIFIED POINTS:\n"
        "- Basic definition of candidate keys.\n"
        "FLAGGED ISSUES:\n"
        "- Mentions 5NF and join dependencies which are outside course materials.\n"
        "SUGGESTED REVISION:\n"
        "Scope explanation to 3NF and BCNF according to [Lecture: dbms.pdf, Page 3].\n"
    )

    result = RevisorEngine.parse_model_output(model_output, citations)
    assert result.audit_status == GroundedAuditStatus.UNGROUNDED_CLAIM_DETECTED
    assert result.is_approved is False
    assert len(result.flagged_issues) == 1
    assert "outside course materials" in result.flagged_issues[0]


def test_revisor_deterministic_closure_check_pass() -> None:
    """Deterministic check passes when closure claim is mathematically correct."""
    # Correct claim: closure of {A} under A -> B, B -> C is {A, B, C}
    cand = "The closure of {A} under A -> B, B -> C is {A, B, C}."
    checks = RevisorEngine.verify_deterministic_claims(cand)
    assert checks["contradiction_detected"] is False


def test_revisor_deterministic_closure_check_fail() -> None:
    """Deterministic check catches mathematical fallacy."""
    # Wrong claim: closure of {A} under A -> B is {A, B, C} (C cannot be derived)
    cand = "The closure of {A} under A -> B is {A, B, C}."
    checks = RevisorEngine.verify_deterministic_claims(cand)
    assert checks["contradiction_detected"] is True
    reason = checks.get("contradiction_reason", "")
    assert "Deterministic" in reason or "closure" in reason


def test_deterministic_check_overrides_llm_false_approval() -> None:
    """ADR 0002 rule: If deterministic logic flags a contradiction, LLM approval is overridden."""
    citations = ["[Lecture: dbms.pdf, Page 1]"]
    # Model mistakenly approves:
    model_output = (
        "STATUS: VERIFIED_GROUNDED\n"
        "SUMMARY: Everything looks completely sound.\n"
        "VERIFIED POINTS:\n"
        "- All claims approved.\n"
        "FLAGGED ISSUES:\n"
        "None\n"
    )
    # But deterministic logic caught an invalid closure!
    det_checks = {
        "contradiction_detected": True,
        "contradiction_reason": (
            "Claimed closure of {A} is {A, B, C}, but actual closure is {A, B}."
        ),
    }

    result = RevisorEngine.parse_model_output(
        model_output,
        citations,
        deterministic_checks=det_checks,
    )
    # Status MUST be CONTRADICTION_DETECTED and is_approved MUST be False!
    assert result.audit_status == GroundedAuditStatus.CONTRADICTION_DETECTED
    assert result.is_approved is False
    assert any("Deterministic logic failure" in issue for issue in result.flagged_issues)
