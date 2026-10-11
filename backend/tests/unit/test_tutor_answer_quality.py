"""Automated regression and quality tests for Tutor answer quality, adaptive structure, and template leakage prevention."""

import pytest
from app.modules.ai_engine.tutor_engine import GroundedTutorEngine
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch


@pytest.mark.unit
def test_tutor_3nf_regression_question_factual_and_structural_correctness() -> None:
    """Verify that the exact student regression question receives a correct 3NF verdict and decomposition."""
    student_query = (
        "Consider a relation EMPLOYEE_DEPT that stores details about company employees and their departments:\n\n"
        "Schema: EMPLOYEE_DEPT (Emp_ID, Emp_Name, Dept_ID, Dept_Name)\n\n"
        "Primary Key: Emp_ID\n\n"
        "Functional Dependencies:\n"
        "1. Emp_ID → Emp_Name\n"
        "2. Emp_ID → Dept_ID\n"
        "3. Dept_ID → Dept_Name\n\n"
        "Check if the above is in 3NF; if not, convert it into 3NF."
    )
    citations = ["[Lecture: dbms_normalization.md, Page 5]"]

    # Test sanitization and domain repair on raw model output
    raw_response = (
        "### Verdict: Not In 3NF #\n"
        "The relation is not in 3NF because Dept_ID -> Dept_Name is a transitive dependency.\n\n"
        "### Candidate Key\n"
        "Emp_ID determines all attributes so Emp_ID is the candidate key.\n\n"
        "### Decomposition\n"
        "EMPLOYEE(Emp_ID, Emp_Name, Dept_ID) and DEPARTMENT(Dept_ID, Dept_Name)."
    )

    result = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=raw_response,
        citations=citations,
        query=student_query,
    )

    # 1. Check verdict correctness: NOT in 3NF
    assert "not in 3nf" in result.lower()
    assert "not claim that the original relation is in 3nf" not in result.lower()

    # 2. Check Candidate Key
    assert "Emp_ID" in result

    # 3. Check 3NF violation: Dept_ID -> Dept_Name
    assert "Dept_ID" in result
    assert "Dept_Name" in result

    # 4. Check canonical 3NF decomposition: EMPLOYEE & DEPARTMENT
    assert "EMPLOYEE" in result
    assert "DEPARTMENT" in result
    assert "Emp_Name" in result
    assert "Dept_Name" in result

    # 5. Check Lossless Join & Dependency Preservation properties
    assert "Lossless" in result or "lossless" in result
    assert "Preservation" in result or "preserv" in result

    # 6. Check template leakage prevention: NO literal '#' at the end of headings
    lines = result.split("\n")
    for line in lines:
        if line.startswith("#"):
            assert not line.endswith("#"), f"Heading ends with literal '#': {line}"
            assert "#" not in line.lstrip("#").strip(), f"Heading contains trailing hash symbol: {line}"
            assert "DIRECT ANSWER #" not in line
            assert "CORE CONCEPT #" not in line
            assert "STEP BY STEP BREAKDOWN #" not in line
            assert "WORKED EXAMPLE #" not in line


@pytest.mark.unit
def test_tutor_cleans_template_leakage_and_trailing_hashes() -> None:
    """Verify that headings with trailing hashes or template placeholders are cleanly sanitized."""
    malformed_markdown = (
        "### Direct Answer #\n"
        "Boyce-Codd Normal Form eliminates all functional dependency anomalies.\n\n"
        "### Core Concept ###\n"
        "Every determinant must be a superkey in BCNF.\n\n"
        "### Step-by-Step Breakdown :\n"
        "1. Find candidate keys.\n"
        "2. Check each non-trivial FD X -> Y.\n"
    )

    cleaned = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=malformed_markdown,
        citations=["[Lecture: dbms_normalization.md]"],
        query="What is BCNF?",
    )

    assert "### Direct Answer" in cleaned
    assert "### Direct Answer #" not in cleaned
    assert "### Core Concept" in cleaned
    assert "### Core Concept ###" not in cleaned
    assert "### Step-by-Step Breakdown" in cleaned
    assert "### Step-by-Step Breakdown :" not in cleaned


@pytest.mark.unit
def test_tutor_adaptive_short_factual_question() -> None:
    """Verify that short factual questions do not force boilerplate headings or unnecessary sections."""
    short_query = "What is the port number for HTTP?"
    short_raw = "The standard port number for unencrypted HTTP traffic is port 80."

    result = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=short_raw,
        citations=["[Lecture: networking.md]"],
        query=short_query,
    )

    # Should remain concise and not inject empty sections or 7 forced headings
    assert "port 80" in result
    assert "### 📌 Direct Answer" not in result
    assert "### 💡 Concrete Worked Example" not in result


@pytest.mark.unit
def test_tutor_abstains_honestly_when_insufficient_evidence() -> None:
    """Verify that honest abstention message is returned when model signals insufficient material."""
    empty_or_abstain = "I do not have sufficient information in the official course materials to answer this question."
    result = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=empty_or_abstain,
        citations=[],
        query="Explain quantum computing.",
    )
    assert result == GroundedTutorEngine.ABSTENTION_MESSAGE


@pytest.mark.unit
def test_tutor_prompt_assembler_adapts_by_question_type() -> None:
    """Verify that GroundedTutorEngine.assemble_prompt adapts instructions for normalization questions."""
    matches = [
        RetrievalMatch(
            chunk_id="c-1",
            document_id="d-1",
            document_filename="dbms_normalization.md",
            page_number=1,
            content="Functional dependencies and normal forms.",
            similarity_score=0.95,
            citation="[Lecture: dbms_normalization.md, Page 1]",
            metadata_attributes={},
        )
    ]

    norm_query = "Check if relation R(A, B, C) with A->B and B->C is in 3NF; if not convert it."
    prompt = GroundedTutorEngine.assemble_prompt(
        query=norm_query,
        matches=matches,
        max_context_chars=1000,
    )

    assert "NORMALIZATION REQUIREMENTS" in prompt.user_prompt
    assert "STUDENT QUESTION:" in prompt.user_prompt
    assert norm_query in prompt.user_prompt
    assert len(prompt.citations) == 1
