"""Unit tests for CurriculumValidator, ambiguity detection, and arbitrary DAG cycle detection."""

import pytest

from app.core.errors import RecallException
from app.models.curriculum import LearningObjective
from app.services.curriculum_service import CurriculumValidator


def test_detect_cycle_empty_and_valid_dag() -> None:
    # Empty graph
    assert CurriculumValidator.detect_cycle_in_graph({}) is None

    # Linear DAG: A requires B, B requires C, C requires nothing
    linear_graph = {
        "A": ["B"],
        "B": ["C"],
        "C": [],
    }
    assert CurriculumValidator.detect_cycle_in_graph(linear_graph) is None

    # Diamond DAG: A -> B, A -> C, B -> D, C -> D
    diamond_graph = {
        "A": ["B", "C"],
        "B": ["D"],
        "C": ["D"],
        "D": [],
    }
    assert CurriculumValidator.detect_cycle_in_graph(diamond_graph) is None


def test_detect_cycle_self_loop() -> None:
    graph = {"A": ["A"]}
    cycle = CurriculumValidator.detect_cycle_in_graph(graph)
    assert cycle is not None
    assert cycle == ["A", "A"]


def test_detect_cycle_two_node() -> None:
    graph = {
        "A": ["B"],
        "B": ["A"],
    }
    cycle = CurriculumValidator.detect_cycle_in_graph(graph)
    assert cycle is not None
    assert cycle == ["A", "B", "A"]


def test_detect_cycle_three_node() -> None:
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["A"],
    }
    cycle = CurriculumValidator.detect_cycle_in_graph(graph)
    assert cycle is not None
    assert cycle == ["A", "B", "C", "A"]


def test_detect_cycle_five_node() -> None:
    graph = {
        "A": ["B"],
        "B": ["C"],
        "C": ["D"],
        "D": ["E"],
        "E": ["A"],
    }
    cycle = CurriculumValidator.detect_cycle_in_graph(graph)
    assert cycle is not None
    assert cycle == ["A", "B", "C", "D", "E", "A"]


def test_detect_cycle_disconnected_component() -> None:
    graph = {
        # Valid DAG component
        "X": ["Y"],
        "Y": [],
        # Cyclic component
        "M": ["N"],
        "N": ["P"],
        "P": ["M"],
    }
    cycle = CurriculumValidator.detect_cycle_in_graph(graph)
    assert cycle is not None
    assert cycle == ["M", "N", "P", "M"]


def test_validate_new_objective_duplicate_code_in_same_topic() -> None:
    existing = [
        LearningObjective(
            id="lo-1",
            topic_id="topic-1",
            code="LO_EXISTING",
            title="Existing",
            description="",
            order_index=1,
            prerequisite_objective_ids=[],
        )
    ]
    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-1",
            proposed_code="LO_EXISTING",
            proposed_prerequisites=[],
            existing_objectives=existing,
        )
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "OBJECTIVE_ALREADY_EXISTS"


def test_validate_new_objective_duplicate_code_across_topics_and_ambiguity() -> None:
    # Schema allows same code across different topics in the course
    lo_top1 = LearningObjective(
        id="uuid-t1-intro",
        topic_id="topic-1",
        code="LO_INTRO",
        title="Intro in Topic 1",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    lo_top2 = LearningObjective(
        id="uuid-t2-intro",
        topic_id="topic-2",
        code="LO_INTRO",
        title="Intro in Topic 2",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    existing = [lo_top1, lo_top2]

    # 1. Proposing a new objective referencing 'LO_INTRO' by code is ambiguous
    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-3",
            proposed_code="LO_ADVANCED",
            proposed_prerequisites=["LO_INTRO"],
            existing_objectives=existing,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "AMBIGUOUS_PREREQUISITE"
    assert "matches multiple objectives" in exc_info.value.detail

    # 2. Referencing the desired objective by its specific UUID resolves unambiguously
    CurriculumValidator.validate_new_objective(
        course_id="course-1",
        topic_id="topic-3",
        proposed_code="LO_ADVANCED_1",
        proposed_prerequisites=["uuid-t1-intro"],
        existing_objectives=existing,
    )

    # 3. Referencing the other objective by its specific UUID also resolves unambiguously
    CurriculumValidator.validate_new_objective(
        course_id="course-1",
        topic_id="topic-3",
        proposed_code="LO_ADVANCED_2",
        proposed_prerequisites=["uuid-t2-intro"],
        existing_objectives=existing,
    )


def test_validate_new_objective_self_prerequisite() -> None:
    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-1",
            proposed_code="LO_SELF",
            proposed_prerequisites=["LO_SELF"],
            existing_objectives=[],
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "CYCLIC_PREREQUISITE"


def test_validate_new_objective_unresolved_prerequisite() -> None:
    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-1",
            proposed_code="LO_NEW",
            proposed_prerequisites=["LO_UNKNOWN"],
            existing_objectives=[],
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "UNRESOLVED_PREREQUISITE"


def test_validate_new_objective_cross_topic_and_by_id_resolution() -> None:
    # Objectives in two different topics of the SAME course
    lo1 = LearningObjective(
        id="uuid-lo-1",
        topic_id="topic-1",
        code="LO_TOPIC1",
        title="Topic 1 LO",
        description="",
        order_index=1,
        prerequisite_objective_ids=[],
    )
    lo2 = LearningObjective(
        id="uuid-lo-2",
        topic_id="topic-2",
        code="LO_TOPIC2",
        title="Topic 2 LO",
        description="",
        order_index=1,
        prerequisite_objective_ids=["LO_TOPIC1"],
    )
    existing = [lo1, lo2]

    # Reference by ID from topic-2
    CurriculumValidator.validate_new_objective(
        course_id="course-1",
        topic_id="topic-2",
        proposed_code="LO_NEW_BY_ID",
        proposed_prerequisites=["uuid-lo-1"],
        existing_objectives=existing,
    )

    # Reference by code across topics
    CurriculumValidator.validate_new_objective(
        course_id="course-1",
        topic_id="topic-2",
        proposed_code="LO_NEW_BY_CODE",
        proposed_prerequisites=["LO_TOPIC1"],
        existing_objectives=existing,
    )


def test_validate_new_objective_cross_topic_cycle() -> None:
    # Cross-topic cycle: LO_1 in topic-1 requires LO_2 in topic-2, LO_2 requires LO_1
    lo_1 = LearningObjective(
        id="id-t1-lo1",
        topic_id="topic-1",
        code="LO_T1_1",
        title="Topic 1 Objective",
        description="",
        order_index=1,
        prerequisite_objective_ids=["LO_T2_2"],
    )
    existing = [lo_1]

    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-2",
            proposed_code="LO_T2_2",
            proposed_prerequisites=["LO_T1_1"],
            existing_objectives=existing,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "CYCLIC_PREREQUISITE"
    assert "LO_T2_2 -> LO_T1_1 -> LO_T2_2" in exc_info.value.detail


def test_validate_new_objective_three_node_cycle() -> None:
    # Existing: LO_A -> LO_B, LO_B -> LO_C
    lo_a = LearningObjective(
        id="id-a",
        topic_id="topic-1",
        code="LO_A",
        title="A",
        description="",
        order_index=1,
        prerequisite_objective_ids=["LO_B"],
    )
    lo_b = LearningObjective(
        id="id-b",
        topic_id="topic-1",
        code="LO_B",
        title="B",
        description="",
        order_index=2,
        prerequisite_objective_ids=["LO_C"],
    )
    existing = [lo_a, lo_b]

    # Proposed LO_C requires LO_A -> creates LO_C -> LO_A -> LO_B -> LO_C cycle
    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-1",
            proposed_code="LO_C",
            proposed_prerequisites=["LO_A"],
            existing_objectives=existing,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "CYCLIC_PREREQUISITE"
    assert "LO_C -> LO_A -> LO_B -> LO_C" in exc_info.value.detail


def test_validate_new_objective_preexisting_malformed_reference() -> None:
    # Pre-existing objective in DB has an invalid prerequisite that doesn't exist
    lo_broken = LearningObjective(
        id="id-broken",
        topic_id="topic-1",
        code="LO_BROKEN",
        title="Broken",
        description="",
        order_index=1,
        prerequisite_objective_ids=["NON_EXISTENT_ID"],
    )
    existing = [lo_broken]

    # Validator refuses to silently ignore the broken pre-existing edge
    with pytest.raises(RecallException) as exc_info:
        CurriculumValidator.validate_new_objective(
            course_id="course-1",
            topic_id="topic-1",
            proposed_code="LO_NEW",
            proposed_prerequisites=[],
            existing_objectives=existing,
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.code == "UNRESOLVED_PREREQUISITE"
    assert "Existing objective 'LO_BROKEN'" in exc_info.value.detail
