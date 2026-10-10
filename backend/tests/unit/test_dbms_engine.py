"""Unit tests for the Deterministic Relational DBMS Algorithm Engine."""

import pytest
from app.modules.adaptive_learning.dbms_engine import (
    are_fd_sets_equivalent,
    check_normal_form,
    compute_attribute_closure,
    compute_minimal_cover,
    find_all_candidate_keys,
    is_dependency_preserving,
    is_lossless_join,
    is_superkey,
    parse_attributes,
    parse_fd,
    parse_fd_list,
)


@pytest.mark.unit
def test_parse_attributes_and_fds() -> None:
    attrs1 = parse_attributes("A, B, C")
    assert attrs1 == {"A", "B", "C"}

    attrs2 = parse_attributes("ABC")
    assert attrs2 == {"A", "B", "C"}

    lhs, rhs = parse_fd("AB -> C")
    assert lhs == frozenset({"A", "B"})
    assert rhs == frozenset({"C"})

    lhs2, rhs2 = parse_fd("X → Y")
    assert lhs2 == frozenset({"X"})
    assert rhs2 == frozenset({"Y"})


@pytest.mark.unit
def test_attribute_closure_transitive_chain() -> None:
    fds = parse_fd_list(["A -> B", "B -> C", "C -> D"])
    closure_a = compute_attribute_closure({"A"}, fds)
    assert closure_a == {"A", "B", "C", "D"}

    closure_b = compute_attribute_closure({"B"}, fds)
    assert closure_b == {"B", "C", "D"}


@pytest.mark.unit
def test_candidate_keys_multiple_and_cyclic() -> None:
    # R(A, B, C, D) with {A -> B, BC -> D, D -> A}
    fds = parse_fd_list(["A -> B", "BC -> D", "D -> A"])
    relation_attrs = {"A", "B", "C", "D"}
    candidate_keys = find_all_candidate_keys(relation_attrs, fds)

    assert candidate_keys == {
        frozenset({"A", "C"}),
        frozenset({"B", "C"}),
        frozenset({"C", "D"}),
    }

    # Cyclic: W -> X -> Y -> Z -> W
    cyclic_fds = parse_fd_list(["W -> X", "X -> Y", "Y -> Z", "Z -> W"])
    cyclic_attrs = {"W", "X", "Y", "Z"}
    cyclic_keys = find_all_candidate_keys(cyclic_attrs, cyclic_fds)
    assert cyclic_keys == {
        frozenset({"W"}),
        frozenset({"X"}),
        frozenset({"Y"}),
        frozenset({"Z"}),
    }


@pytest.mark.unit
def test_minimal_cover_computation() -> None:
    # F = {A -> B, A -> C, B -> C, AB -> C}
    # Minimal cover should be {A -> B, B -> C}
    fds = parse_fd_list(["A -> B", "A -> C", "B -> C", "AB -> C"])
    cover = compute_minimal_cover(fds)

    expected = parse_fd_list(["A -> B", "B -> C"])
    assert are_fd_sets_equivalent(cover, expected)
    assert len(cover) == 2


@pytest.mark.unit
def test_normal_form_diagnostics() -> None:
    # 2NF Violation: R(A, B, C, D), key AB, FD B -> D (partial dependency)
    fds_2nf_viol = parse_fd_list(["AB -> C", "B -> D"])
    res1 = check_normal_form({"A", "B", "C", "D"}, fds_2nf_viol)
    assert res1["highest_normal_form"] == "1NF"
    assert len(res1["violations"]["2NF"]) >= 1

    # 3NF but not BCNF: R(A, B, C), keys AB and AC, FDs {AB -> C, C -> B}
    fds_3nf = parse_fd_list(["AB -> C", "C -> B"])
    res2 = check_normal_form({"A", "B", "C"}, fds_3nf)
    assert res2["highest_normal_form"] == "3NF"
    assert len(res2["violations"]["BCNF"]) >= 1
    assert len(res2["violations"]["3NF"]) == 0

    # BCNF relation: R(A, B, C), key A, FDs {A -> B, B -> C} decomposed to R1(A, B), R2(B, C)
    res_bcnf1 = check_normal_form({"A", "B"}, parse_fd_list(["A -> B"]))
    assert res_bcnf1["highest_normal_form"] == "BCNF"


@pytest.mark.unit
def test_lossless_join_two_way_and_chase() -> None:
    fds = parse_fd_list(["A -> B", "B -> C"])
    rel_attrs = {"A", "B", "C"}

    # Lossless: R1(A, B), R2(B, C) -> R1 ∩ R2 = {B}, B -> BC covers R2
    decomps_lossless = [{"A", "B"}, {"B", "C"}]
    assert is_lossless_join(rel_attrs, decomps_lossless, fds) is True

    # Lossy: R1(A, B), R2(A, C) with F = {B -> C}
    fds_lossy = parse_fd_list(["B -> C"])
    decomps_lossy = [{"A", "B"}, {"A", "C"}]
    assert is_lossless_join(rel_attrs, decomps_lossy, fds_lossy) is False

    # n-way Chase algorithm test: R(A, B, C, D), D = {AB, BC, CD}, F = {A -> B, B -> C, C -> D}
    rel_4 = {"A", "B", "C", "D"}
    fds_4 = parse_fd_list(["A -> B", "B -> C", "C -> D"])
    decomps_4 = [{"A", "B"}, {"B", "C"}, {"C", "D"}]
    assert is_lossless_join(rel_4, decomps_4, fds_4) is True


@pytest.mark.unit
def test_dependency_preservation() -> None:
    # R(A, B, C) with {A -> B, B -> C, C -> A} decomposed to {AB, BC}
    # In AB, A -> B is preserved. In BC, B -> C is preserved.
    # Closure of C under projected FDs: C -> A is preserved via C -> A in closure!
    fds = parse_fd_list(["A -> B", "B -> C", "C -> A"])
    decomps = [{"A", "B"}, {"B", "C"}]
    assert is_dependency_preserving(decomps, fds) is True

    # R(A, B, C) with {AB -> C, C -> B} decomposed to {AC, BC}
    # AB -> C is lost!
    fds_loss = parse_fd_list(["AB -> C", "C -> B"])
    decomps_loss = [{"A", "C"}, {"B", "C"}]
    assert is_dependency_preserving(decomps_loss, fds_loss) is False
