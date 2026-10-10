"""Deterministic Mastery and Evidence Estimation Engine.

Implements the frozen learning rules:
1. Evidence-Confidence Decoupling (Performance P_k in [0, 1] vs Confidence C_k in [0, 1]).
2. Non-Catastrophic Diagnosis (single failures trigger diagnostic probing,
   not catastrophic collapse).
3. Non-Duplicate Evidence (repeat attempts on same question ID do not inflate evidence volume).
4. Hint Degradation (hint-assisted attempts have discounted evidence weight).
5. Hypothetical Prerequisites (prerequisite satisfaction evaluated without causal imputation).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.models.attempt import Attempt
from app.models.curriculum import LearningObjective


class MasteryState(str, Enum):
    """Categorical mastery classification."""

    UNTESTED = "untested"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NEEDS_REMEDIATION = "needs_remediation"
    DEVELOPING = "developing"
    MASTERED = "mastered"


@dataclass
class ObjectiveMasteryProfile:
    """Deterministic mastery and evidence estimation for a single learning objective."""

    objective_id: str
    objective_code: str
    performance_score: float  # P_k in [0.0, 1.0]
    confidence_score: float  # C_k in [0.0, 1.0]
    mastery_state: MasteryState
    prerequisites_satisfied: bool
    blocked_by_prerequisites: list[str] = field(default_factory=list)
    total_attempts: int = 0
    distinct_questions_attempted: int = 0
    unassisted_correct_count: int = 0
    hint_assisted_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)


class MasteryEngine:
    """Authoritative deterministic mastery calculation engine."""

    CONFIDENCE_THRESHOLD: float = 0.50
    MIN_INDEPENDENT_EVIDENCE_FOR_FULL_CONFIDENCE: float = 3.0
    PASSING_PERFORMANCE_THRESHOLD: float = 0.60
    MASTERY_PERFORMANCE_THRESHOLD: float = 0.85
    HINT_EVIDENCE_WEIGHT: float = 0.35  # Rule 4: Whint <= 0.35

    @classmethod
    def compute_objective_mastery(
        cls,
        objective: LearningObjective,
        attempts: list[Attempt],
        prerequisite_profiles: dict[str, "ObjectiveMasteryProfile"] | None = None,
    ) -> ObjectiveMasteryProfile:
        """Compute deterministic mastery profile for an objective from its attempt ledger.

        Args:
            objective: The canonical learning objective.
            attempts: All historical attempts associated with questions for this objective.
            prerequisite_profiles: Mapping of prerequisite objective code/id to their profile.
        """
        prerequisite_profiles = prerequisite_profiles or {}

        if not attempts:
            prereq_satisfied, blocked_by = cls._check_prerequisites(
                objective, prerequisite_profiles
            )
            return ObjectiveMasteryProfile(
                objective_id=objective.id,
                objective_code=objective.code,
                performance_score=0.0,
                confidence_score=0.0,
                mastery_state=MasteryState.UNTESTED,
                prerequisites_satisfied=prereq_satisfied,
                blocked_by_prerequisites=blocked_by,
                total_attempts=0,
                distinct_questions_attempted=0,
                unassisted_correct_count=0,
                hint_assisted_count=0,
                details={"reason": "No recorded attempts for this objective."},
            )

        # 1. Group attempts by distinct question_id (Rule 3: Non-Duplicate Evidence)
        attempts_by_question: dict[str, list[Attempt]] = {}
        for att in attempts:
            attempts_by_question.setdefault(att.question_id, []).append(att)

        distinct_q_count = len(attempts_by_question)
        total_attempts = len(attempts)

        weighted_score_sum = 0.0
        total_evidence_weight = 0.0
        unassisted_correct = 0
        hint_assisted_count = 0

        # 2. For each distinct question, calculate effective evidence weight and performance
        for _q_id, q_attempts in attempts_by_question.items():
            # Sort attempts chronologically
            sorted_atts = sorted(
                q_attempts,
                key=lambda a: (
                    a.created_at.timestamp()
                    if a.created_at is not None
                    else (
                        a.submitted_at.timestamp()
                        if a.submitted_at is not None
                        else 0.0
                    )
                ),
            )

            # Look at the best verified attempt on this question
            best_att = max(
                sorted_atts,
                key=lambda a: (a.score_achieved / max(a.max_possible_score, 1e-6)),
            )

            ratio = (
                best_att.score_achieved / best_att.max_possible_score
                if best_att.max_possible_score > 0
                else 0.0
            )
            ratio = max(0.0, min(1.0, ratio))

            # Determine evidence weight (Rule 4: Hint Degradation)
            if best_att.is_hint_assisted and best_att.hint_count > 0:
                evidence_weight = cls.HINT_EVIDENCE_WEIGHT
                hint_assisted_count += 1
            else:
                evidence_weight = 1.0
                if best_att.is_correct:
                    unassisted_correct += 1

            # Repeat attempts on same question ID do not grant fresh independent weight (Rule 3)
            # The question contributes at most 1 distinct evidence unit
            weighted_score_sum += ratio * evidence_weight
            total_evidence_weight += evidence_weight

        # 3. Compute Performance Score P_k in [0.0, 1.0]
        performance_score = (
            weighted_score_sum / total_evidence_weight
            if total_evidence_weight > 0
            else 0.0
        )
        performance_score = round(max(0.0, min(1.0, performance_score)), 4)

        # 4. Compute Evidence Confidence C_k in [0.0, 1.0] (Rule 1: Decoupled from P_k)
        confidence_score = min(
            1.0,
            total_evidence_weight / cls.MIN_INDEPENDENT_EVIDENCE_FOR_FULL_CONFIDENCE,
        )
        confidence_score = round(max(0.0, min(1.0, confidence_score)), 4)

        # 5. Evaluate Prerequisite Satisfaction (Rule 5: Hypothetical Prerequisites)
        prereq_satisfied, blocked_by = cls._check_prerequisites(
            objective, prerequisite_profiles
        )

        # 6. Determine Mastery State Transition
        if confidence_score < cls.CONFIDENCE_THRESHOLD:
            # Rule 2: Non-Catastrophic Diagnosis - insufficient volume prevents collapse
            mastery_state = MasteryState.INSUFFICIENT_EVIDENCE
        elif performance_score >= cls.MASTERY_PERFORMANCE_THRESHOLD:
            mastery_state = MasteryState.MASTERED
        elif performance_score >= cls.PASSING_PERFORMANCE_THRESHOLD:
            mastery_state = MasteryState.DEVELOPING
        else:
            mastery_state = MasteryState.NEEDS_REMEDIATION

        return ObjectiveMasteryProfile(
            objective_id=objective.id,
            objective_code=objective.code,
            performance_score=performance_score,
            confidence_score=confidence_score,
            mastery_state=mastery_state,
            prerequisites_satisfied=prereq_satisfied,
            blocked_by_prerequisites=blocked_by,
            total_attempts=total_attempts,
            distinct_questions_attempted=distinct_q_count,
            unassisted_correct_count=unassisted_correct,
            hint_assisted_count=hint_assisted_count,
            details={
                "total_evidence_weight": round(total_evidence_weight, 3),
                "weighted_score_sum": round(weighted_score_sum, 3),
                "confidence_threshold": cls.CONFIDENCE_THRESHOLD,
                "passing_threshold": cls.PASSING_PERFORMANCE_THRESHOLD,
                "mastery_threshold": cls.MASTERY_PERFORMANCE_THRESHOLD,
            },
        )

    @classmethod
    def _check_prerequisites(
        cls,
        objective: LearningObjective,
        prerequisite_profiles: dict[str, "ObjectiveMasteryProfile"],
    ) -> tuple[bool, list[str]]:
        """Verify whether all prerequisite hypotheses are satisfied."""
        blocked_by: list[str] = []

        for p_ref in objective.prerequisite_objective_ids:
            p_prof = prerequisite_profiles.get(p_ref)
            if not p_prof:
                # If prerequisite profile is missing or untested, mark as blocked
                blocked_by.append(p_ref)
            elif p_prof.mastery_state in (
                MasteryState.NEEDS_REMEDIATION,
                MasteryState.UNTESTED,
            ):
                blocked_by.append(p_ref)

        return (len(blocked_by) == 0, blocked_by)
