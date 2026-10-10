"""Deterministic Evaluator for Relational DBMS and Foundational Learning Objectives."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.modules.adaptive_learning.dbms_engine import (
    FDType,
    are_fd_sets_equivalent,
    check_normal_form,
    compute_minimal_cover,
    is_dependency_preserving,
    is_lossless_join,
    parse_attributes,
    parse_fd,
    parse_fd_list,
)


@dataclass
class GradingOutcome:
    """Immutable outcome of deterministic question evaluation."""

    is_correct: bool
    score_achieved: float
    max_possible_score: float
    provenance: dict[str, Any] = field(default_factory=dict)


class DBMSDeterministicGrader:
    """Authoritative deterministic grader for DBMS and general assessment items."""

    @classmethod
    def grade(
        cls,
        question_type: str,
        answer_key: dict[str, Any],
        rubric: dict[str, Any],
        submitted_answer: dict[str, Any],
        max_score: float = 1.0,
        is_hint_assisted: bool = False,
        hint_count: int = 0,
        prior_attempt_count: int = 0,
    ) -> GradingOutcome:
        """Deterministically grade submitted_answer against answer_key and rubric."""
        rubric_type = rubric.get("type", "exact_match")
        is_correct = False
        base_score = 0.0
        evaluation_steps: list[str] = []
        deductions: list[dict[str, Any]] = []

        if rubric_type == "attribute_closure":
            # 1. Attribute Closure Evaluation
            expected_attrs = parse_attributes(
                answer_key.get("closure") or answer_key.get("value", "")
            )
            actual_attrs = parse_attributes(
                submitted_answer.get("closure") or submitted_answer.get("value", "")
            )

            evaluation_steps.append(
                f"Attribute closure evaluation: expected={sorted(expected_attrs)}, "
                f"submitted={sorted(actual_attrs)}"
            )

            if actual_attrs == expected_attrs:
                is_correct = True
                base_score = max_score
                evaluation_steps.append("Exact attribute closure match confirmed.")
            else:
                missing = expected_attrs - actual_attrs
                extra = actual_attrs - expected_attrs
                if missing:
                    deductions.append(
                        {"reason": "Missing attributes in closure", "attributes": sorted(missing)}
                    )
                if extra:
                    deductions.append(
                        {
                            "reason": "Extraneous attributes not in closure",
                            "attributes": sorted(extra),
                        }
                    )

        elif rubric_type == "candidate_keys":
            # 2. Candidate Keys Evaluation
            expected_raw = answer_key.get("candidate_keys", [])
            expected_keys: set[frozenset[str]] = {
                frozenset(parse_attributes(k)) for k in expected_raw
            }

            actual_raw = submitted_answer.get("candidate_keys") or submitted_answer.get("value", [])
            if isinstance(actual_raw, str):
                actual_raw = [actual_raw]
            actual_keys: set[frozenset[str]] = {
                frozenset(parse_attributes(k)) for k in actual_raw
            }

            exp_repr = sorted(["".join(sorted(k)) for k in expected_keys])
            act_repr = sorted(["".join(sorted(k)) for k in actual_keys])
            evaluation_steps.append(
                f"Candidate keys evaluation: expected={exp_repr}, submitted={act_repr}"
            )

            if actual_keys == expected_keys:
                is_correct = True
                base_score = max_score
                evaluation_steps.append("All candidate keys correctly and minimally identified.")
            else:
                missing_keys = expected_keys - actual_keys
                extra_keys = actual_keys - expected_keys
                if missing_keys:
                    deductions.append({
                        "reason": "Missing candidate keys",
                        "keys": sorted(["".join(sorted(k)) for k in missing_keys]),
                    })
                if extra_keys:
                    deductions.append({
                        "reason": "Spurious or non-minimal keys submitted",
                        "keys": sorted(["".join(sorted(k)) for k in extra_keys]),
                    })

        elif rubric_type == "minimal_cover":
            # 3. Minimal Cover Evaluation
            expected_fds = parse_fd_list(answer_key.get("fds", []))
            actual_raw_fds = (
                submitted_answer.get("fds")
                or submitted_answer.get("value", [])
            )
            if isinstance(actual_raw_fds, str):
                actual_raw_fds = [s.strip() for s in actual_raw_fds.split(";") if s.strip()]
            elif not isinstance(actual_raw_fds, list):
                actual_raw_fds = [str(actual_raw_fds)]

            actual_fds: list[FDType] = []
            malformed_syntax: list[str] = []
            for item in actual_raw_fds:
                try:
                    actual_fds.append(parse_fd(str(item)))
                except ValueError:
                    malformed_syntax.append(str(item))

            if malformed_syntax:
                deductions.append(
                    {
                        "reason": "Malformed functional dependency syntax (expected '->' or '→')",
                        "malformed": malformed_syntax,
                    }
                )

            # Check 1: Singleton RHS
            has_singleton_rhs = (
                bool(actual_fds) and all(len(rhs) == 1 for _, rhs in actual_fds)
            )
            if not has_singleton_rhs and not malformed_syntax:
                deductions.append(
                    {"reason": "Not all functional dependencies have singleton RHS"}
                )

            # Check 2: Closure Equivalence
            equiv = bool(actual_fds) and are_fd_sets_equivalent(actual_fds, expected_fds)
            if not equiv and not malformed_syntax:
                deductions.append(
                    {"reason": "Submitted FDs do not generate equivalent closure to original FDs"}
                )

            # Check 3: Minimality
            canonical_cover = compute_minimal_cover(expected_fds)
            is_minimal = bool(actual_fds) and len(actual_fds) <= len(canonical_cover) and equiv

            if equiv and has_singleton_rhs and is_minimal and not malformed_syntax:
                is_correct = True
                base_score = max_score
                evaluation_steps.append(
                    "Minimal cover validated for singleton RHS, equivalence, and minimality."
                )
            else:
                evaluation_steps.append("Minimal cover criteria failed.")

        elif rubric_type == "decomposition":
            # 4. Normalization Decomposition Evaluation
            rel_attrs = parse_attributes(answer_key.get("relation_attrs", ""))
            fds = parse_fd_list(answer_key.get("fds", []))
            target_nf = rubric.get("target_normal_form", "BCNF")

            sub_relations_raw = (
                submitted_answer.get("relations")
                or submitted_answer.get("value", [])
            )
            if isinstance(sub_relations_raw, str):
                sub_relations_raw = [s.strip() for s in sub_relations_raw.split(";") if s.strip()]
            elif not isinstance(sub_relations_raw, list):
                sub_relations_raw = []

            decomps = [parse_attributes(r) for r in sub_relations_raw]
            if not decomps or any(not r for r in decomps):
                deductions.append(
                    {"reason": "Invalid or empty sub-relations provided in decomposition"}
                )

            # Step 1: Attribute preservation
            union_attrs: set[str] = set()
            for r in decomps:
                union_attrs.update(r)
            attr_preservation = union_attrs == rel_attrs and bool(union_attrs)
            if not attr_preservation and decomps:
                deductions.append(
                    {"reason": "Decomposition does not preserve all original relation attributes"}
                )

            # Step 2: Lossless join test
            lossless = bool(decomps) and is_lossless_join(rel_attrs, decomps, fds)
            if not lossless and decomps:
                deductions.append({"reason": "Decomposition fails lossless-join property"})

            # Step 3: Dependency preservation test
            dep_preserved = is_dependency_preserving(decomps, fds)
            if rubric.get("require_dependency_preservation", False) and not dep_preserved:
                deductions.append(
                    {"reason": "Decomposition does not preserve all functional dependencies"}
                )

            # Step 4: Target normal form check
            nf_satisfied = True
            for r in decomps:
                nf_info = check_normal_form(r, fds)
                if target_nf == "BCNF" and nf_info["highest_normal_form"] != "BCNF":
                    nf_satisfied = False
                    deductions.append({"reason": f"Sub-relation {sorted(r)} violates BCNF"})
                elif target_nf == "3NF" and nf_info["highest_normal_form"] not in ("3NF", "BCNF"):
                    nf_satisfied = False
                    deductions.append({"reason": f"Sub-relation {sorted(r)} violates 3NF"})

            is_correct = attr_preservation and lossless and nf_satisfied
            if rubric.get("require_dependency_preservation", False):
                is_correct = is_correct and dep_preserved

            if is_correct:
                base_score = max_score
                evaluation_steps.append(
                    f"Decomposition passed lossless-join and {target_nf} compliance."
                )

        else:
            # 5. Baseline exact match / multiple choice
            expected_val = str(answer_key.get("value", "")).strip()
            submitted_val = str(submitted_answer.get("value", "")).strip()

            if expected_val.upper() == submitted_val.upper():
                is_correct = True
                base_score = max_score
                evaluation_steps.append("Exact answer key match confirmed.")
            else:
                deductions.append({
                    "reason": "Submitted answer differs from authoritative key",
                    "expected": expected_val,
                    "submitted": submitted_val,
                })

        # Apply hint-assisted discount if applicable (Rule 4: Whint <= 0.35)
        final_score = base_score
        hint_penalty = 0.0
        if is_correct and is_hint_assisted and hint_count > 0:
            hint_penalty = min(0.65, 0.25 * hint_count)
            final_score = max(0.0, base_score * (1.0 - hint_penalty))
            evaluation_steps.append(
                f"Hint penalty: {hint_count} hints used (discount factor: {hint_penalty:.2f})"
            )

        provenance = {
            "evaluator": "DBMSDeterministicGrader",
            "evaluated_at": datetime.now(UTC).isoformat(),
            "rubric_type": rubric_type,
            "is_correct": is_correct,
            "raw_score": base_score,
            "final_score": final_score,
            "max_score": max_score,
            "is_hint_assisted": is_hint_assisted,
            "hint_count": hint_count,
            "hint_penalty": hint_penalty,
            "prior_attempt_count": prior_attempt_count,
            "repetition_discount_applied": prior_attempt_count > 0,
            "evaluation_steps": evaluation_steps,
            "deductions": deductions,
        }

        return GradingOutcome(
            is_correct=is_correct,
            score_achieved=final_score,
            max_possible_score=max_score,
            provenance=provenance,
        )
