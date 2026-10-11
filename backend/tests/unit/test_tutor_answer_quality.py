"""Automated tests for Section 13 Tutor answer structure, reliability, and first-attempt repair."""

import pytest
from app.modules.ai_engine.tutor_engine import GroundedTutorEngine
from app.modules.knowledge_engine.retrieval_engine import RetrievalMatch


@pytest.mark.unit
def test_tutor_response_sanitization_and_repair_on_unstructured_input() -> None:
    """Verify that unstructured narrative responses are converted to the 7-part pedagogical structure on first attempt."""
    raw_unstructured = (
        "Boyce-Codd Normal Form is an institutional standard for database design. "
        "It eliminates redundant data by requiring that every determinant is a superkey. "
        "To check BCNF, first compute candidate keys using Armstrong axioms. "
        "Next, verify each non-trivial dependency X -> Y has X as a superkey. "
        "Finally, decompose any violating relation using the lossless join algorithm. "
        "For example, in relation R(A, B, C) with AB -> C and C -> B, C is not a superkey violating BCNF. "
        "Always ensure 3NF dependency preservation is evaluated before enforcing strict BCNF."
    )
    citations = ["[Lecture: dbms_normalization.md, Section 2]"]

    structured = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=raw_unstructured,
        citations=citations,
    )

    # Verify standard pedagogical headings are present
    assert "### 📌 Direct Answer" in structured
    assert "### 🔍 Core Concept" in structured
    assert "### ⚙️ Step-by-Step Breakdown" in structured
    assert "### 💡 Concrete Worked Example" in structured
    assert "### ⚠️ Common Misconception" in structured
    assert "### 📝 Essential Takeaway" in structured
    assert "### 📚 Authoritative Citations" in structured

    # Verify citation preservation
    assert "dbms_normalization.md" in structured


@pytest.mark.unit
def test_tutor_preserves_already_structured_response() -> None:
    """Verify that responses already containing markdown headings are preserved cleanly without double-nesting."""
    well_structured = (
        "### 📌 Direct Answer\n"
        "• Deadlock is a state where every process in a set is waiting for an event that only another process in the set can cause.\n\n"
        "### 🔍 Core Concept\n"
        "• Coffman conditions define the four simultaneous requirements for deadlock: mutual exclusion, hold and wait, no preemption, and circular wait.\n\n"
        "### ⚙️ Step-by-Step Breakdown\n"
        "• **Step 1**: Identify resource claim edges in the Resource Allocation Graph.\n"
        "• **Step 2**: Check for directed cycles.\n"
        "• **Step 3**: For single-unit resources, a cycle implies guaranteed deadlock.\n\n"
        "### 💡 Concrete Worked Example\n"
        "• **Given**: P1 holds R1 and requests R2; P2 holds R2 and requests R1.\n"
        "• **Result**: Circular wait formed, system is deadlocked.\n\n"
        "### ⚠️ Common Misconception\n"
        "• A cycle in a multi-instance resource graph does not necessarily guarantee deadlock.\n\n"
        "### 📝 Essential Takeaway\n"
        "• Use resource ordering to break the circular wait condition.\n"
    )

    result = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=well_structured,
        citations=["[Lecture: os_deadlocks.md, Page 4]"],
    )

    assert "### 📌 Direct Answer" in result
    assert "### 🔍 Core Concept" in result
    assert "### ⚙️ Step-by-Step Breakdown" in result
    assert "### 💡 Concrete Worked Example" in result
    assert "### ⚠️ Common Misconception" in result
    assert "### 📝 Essential Takeaway" in result


@pytest.mark.unit
def test_tutor_abstains_honestly_when_insufficient_evidence() -> None:
    """Verify that honest abstention message is returned when model signals insufficient material."""
    empty_or_abstain = "I do not have sufficient information in the official course materials to answer this question."
    result = GroundedTutorEngine.sanitize_and_structure_response(
        raw_text=empty_or_abstain,
        citations=[],
    )
    assert result == GroundedTutorEngine.ABSTENTION_MESSAGE


@pytest.mark.unit
def test_tutor_prompt_assembler_context_bounds() -> None:
    """Verify that GroundedTutorEngine.assemble_prompt respects character budgets and citations."""
    matches = [
        RetrievalMatch(
            chunk_id=f"c-{i}",
            document_id=f"d-{i}",
            document_filename=f"lecture_{i}.md",
            page_number=i,
            content=f"Content excerpt number {i} describing operating system concurrency.",
            similarity_score=0.9 - (i * 0.05),
            citation=f"[Lecture: lecture_{i}.md, Page {i}]",
            metadata_attributes={},
        )
        for i in range(1, 5)
    ]

    prompt = GroundedTutorEngine.assemble_prompt(
        query="What is the difference between a process and a thread?",
        matches=matches,
        max_context_chars=1000,
    )

    assert "NON-NEGOTIABLE GROUNDING RULES" in prompt.system_prompt
    assert "PEDAGOGICAL ANSWER STRUCTURE" in prompt.system_prompt
    assert len(prompt.citations) >= 1
    assert "OFFICIAL COURSE EXCERPTS" in prompt.user_prompt
    assert "What is the difference between a process and a thread?" in prompt.user_prompt
