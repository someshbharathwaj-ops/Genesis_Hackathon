"""Deterministic Evidence Representation and Bounded Diagnosis Engine.

Implements the frozen learning and diagnostic rules:
1. Evidence-Confidence Decoupling (P_k in [0, 1] vs C_k in [0, 1]).
2. Non-Catastrophic Diagnosis (single failures trigger diagnostic probing,
   not systemic weakness; misconceptions require repeated or verified patterns).
3. Non-Duplicate Evidence (repeat attempts on same question ID do not inflate evidence).
4. Hint Degradation (hint-assisted attempts have discounted evidence weight).
5. Hypothetical Prerequisites (prerequisite satisfaction evaluated without causal imputation;
   child failure never retroactively fails parent prerequisites).
6. Bounded Diagnostic Probing (strict session budget <= 5 questions to prevent learner exhaustion).
7. Recovery Routing (persistent failure or frustration routes to revision/unscored practice).
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from app.models.attempt import AssessmentContext, Attempt
from app.models.curriculum import LearningObjective


class EvidenceValidity(str, Enum):
    """Classification of an evidence item's validity and independence."""

    VALID_INDEPENDENT = "valid_independent"
    HINT_DEGRADED = "hint_degraded"
    REPETITION_DISCOUNTED = "repetition_discounted"
    UNSCORED_PRACTICE = "unscored_practice"
    UNVERIFIED_EVIDENCE = "unverified_evidence"


class SufficiencyStatus(str, Enum):
    """Categorical evaluation of evidence sufficiency."""

    NO_EVIDENCE = "no_evidence"
    INSUFFICIENT = "insufficient"
    SUFFICIENT = "sufficient"


class DiagnosticStatus(str, Enum):
    """Authoritative diagnostic status for a learning objective."""

    UNTESTED = "untested"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    DEMONSTRATED_WEAKNESS = "demonstrated_weakness"
    DEVELOPING = "developing"
    MASTERED = "mastered"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


class MisconceptionStatus(str, Enum):
    """Validation level for an identified error signature / misconception."""

    CANDIDATE_SIGNAL = (
        "candidate_signal"  # Observed once with low confidence; cannot conclude weakness
    )
    CONFIRMED_MISCONCEPTION = (
        "confirmed_misconception"  # Observed >= 2 times or with sufficient evidence
    )


class DiagnosticAction(str, Enum):
    """Recommended pedagogical next action based on bounded diagnosis."""

    RECOMMEND_DIAGNOSTIC_PROBE = "recommend_diagnostic_probe"
    RECOMMEND_PREREQUISITE_REMEDIATION = "recommend_prerequisite_remediation"
    RECOMMEND_TARGETED_PRACTICE = "recommend_targeted_practice"
    READY_FOR_ADVANCEMENT = "ready_for_advancement"
    GROUNDED_REVISION = "grounded_revision"


@dataclass
class EvidenceItem:
    """Individual evidence unit extracted from an immutable Attempt."""

    attempt_id: str
    question_id: str
    assessment_context: AssessmentContext
    score_ratio: float
    is_correct: bool
    is_hint_assisted: bool
    hint_count: int
    repetition_index: int  # 0 for initial attempt, 1+ for repeats
    effective_weight: float
    validity: EvidenceValidity
    deductions: list[dict[str, Any]]
    submitted_at: datetime | None


@dataclass
class EvidenceLedger:
    """Structured collection of evidence units for an objective."""

    objective_id: str
    total_attempts: int
    valid_independent_count: int
    hint_assisted_count: int
    repetition_count: int
    distinct_questions_count: int
    total_evidence_weight: float
    performance_score: float  # P_k
    confidence_score: float  # C_k
    sufficiency_status: SufficiencyStatus
    is_conflicting: bool
    conflict_reasons: list[str]
    items: list[EvidenceItem] = field(default_factory=list)


@dataclass
class MisconceptionAnalysis:
    """Identified misconception / error signature."""

    signature: str
    description: str
    occurrence_count: int
    status: MisconceptionStatus
    distinct_questions: list[str]
    sample_deduction: dict[str, Any]


@dataclass
class PrerequisiteDiagnosticTrace:
    """Diagnostic hypothesis trace for a prerequisite objective."""

    prerequisite_ref: str
    prerequisite_id: str | None
    prerequisite_code: str | None
    diagnostic_status: DiagnosticStatus
    confidence_score: float
    is_satisfied: bool
    gap_hypothesis: str | None


@dataclass
class BoundedDiagnosticOutcome:
    """Complete explainable diagnostic outcome for a learning objective."""

    objective_id: str
    objective_code: str
    diagnostic_status: DiagnosticStatus
    performance_score: float
    confidence_score: float
    sufficiency_status: SufficiencyStatus
    evidence_ledger: EvidenceLedger
    confirmed_misconceptions: list[MisconceptionAnalysis]
    candidate_signals: list[MisconceptionAnalysis]
    prerequisites_satisfied: bool
    prerequisite_traces: list[PrerequisiteDiagnosticTrace]
    root_cause_attribution: str | None
    recommended_action: DiagnosticAction
    applied_rules: list[str]
    traceable_rationale: str


class BoundedDiagnosisEngine:
    """Authoritative deterministic engine for evidence representation and bounded diagnosis."""

    # Core thresholds
    CONFIDENCE_THRESHOLD: float = 0.50
    MIN_INDEPENDENT_EVIDENCE_FOR_FULL_CONFIDENCE: float = 3.0
    MIN_DISTINCT_QUESTIONS_FOR_SUFFICIENCY: int = 2
    PASSING_PERFORMANCE_THRESHOLD: float = 0.60
    MASTERY_PERFORMANCE_THRESHOLD: float = 0.85
    HINT_EVIDENCE_WEIGHT: float = 0.35  # Rule 4: Whint <= 0.35
    MAX_DIAGNOSTIC_SESSION_QUESTIONS: int = 5  # Strict budget to prevent exhaustion
    MIN_OBSERVATIONS_FOR_CONFIRMED_MISCONCEPTION: int = 2  # Rule 2: Non-catastrophic
    CONFLICT_VARIANCE_THRESHOLD: float = 0.50

    @classmethod
    def compile_evidence_ledger(
        cls,
        objective_id: str,
        attempts: list[Attempt],
    ) -> EvidenceLedger:
        """Parse raw attempts into a deterministic, audited EvidenceLedger."""
        if not attempts:
            return EvidenceLedger(
                objective_id=objective_id,
                total_attempts=0,
                valid_independent_count=0,
                hint_assisted_count=0,
                repetition_count=0,
                distinct_questions_count=0,
                total_evidence_weight=0.0,
                performance_score=0.0,
                confidence_score=0.0,
                sufficiency_status=SufficiencyStatus.NO_EVIDENCE,
                is_conflicting=False,
                conflict_reasons=[],
                items=[],
            )

        # Sort attempts chronologically
        sorted_attempts = sorted(
            attempts,
            key=lambda a: (
                a.created_at.timestamp()
                if a.created_at is not None
                else (a.submitted_at.timestamp() if a.submitted_at is not None else 0.0)
            ),
        )

        items: list[EvidenceItem] = []
        question_attempt_counts: dict[str, int] = {}
        weighted_score_sum = 0.0
        total_evidence_weight = 0.0

        valid_independent_count = 0
        hint_assisted_count = 0
        repetition_count = 0

        # Distinct question effective scores for conflict analysis
        question_ratios: dict[str, list[float]] = {}

        for att in sorted_attempts:
            q_id = att.question_id
            rep_index = question_attempt_counts.get(q_id, 0)
            question_attempt_counts[q_id] = rep_index + 1

            max_score = max(att.max_possible_score, 1e-6)
            ratio = max(0.0, min(1.0, att.score_achieved / max_score))
            question_ratios.setdefault(q_id, []).append(ratio)

            # Extract deductions from provenance
            deductions: list[dict[str, Any]] = []
            if isinstance(att.grading_provenance, dict):
                raw_deductions = att.grading_provenance.get("deductions", [])
                if isinstance(raw_deductions, list):
                    deductions = [d for d in raw_deductions if isinstance(d, dict)]

            # Classify validity and calculate effective weight
            if att.assessment_context == AssessmentContext.UNSCORED_PRACTICE:
                validity = EvidenceValidity.UNSCORED_PRACTICE
                effective_weight = 0.0  # Practice telemetry does not count toward scored evidence
            elif rep_index > 0:
                # Rule 3: Non-Duplicate Evidence
                validity = EvidenceValidity.REPETITION_DISCOUNTED
                effective_weight = 0.0  # Repeats on same question ID do not grant fresh weight
                repetition_count += 1
            elif att.is_hint_assisted and att.hint_count > 0:
                # Rule 4: Hint Degradation
                validity = EvidenceValidity.HINT_DEGRADED
                effective_weight = cls.HINT_EVIDENCE_WEIGHT
                hint_assisted_count += 1
                total_evidence_weight += effective_weight
                weighted_score_sum += ratio * effective_weight
            else:
                validity = EvidenceValidity.VALID_INDEPENDENT
                effective_weight = 1.0
                valid_independent_count += 1
                total_evidence_weight += effective_weight
                weighted_score_sum += ratio * effective_weight

            items.append(
                EvidenceItem(
                    attempt_id=att.id,
                    question_id=q_id,
                    assessment_context=att.assessment_context,
                    score_ratio=round(ratio, 4),
                    is_correct=att.is_correct,
                    is_hint_assisted=att.is_hint_assisted,
                    hint_count=att.hint_count,
                    repetition_index=rep_index,
                    effective_weight=effective_weight,
                    validity=validity,
                    deductions=deductions,
                    submitted_at=att.submitted_at or att.created_at,
                )
            )

        # Compute P_k and C_k
        performance_score = (
            weighted_score_sum / total_evidence_weight if total_evidence_weight > 0 else 0.0
        )
        performance_score = round(max(0.0, min(1.0, performance_score)), 4)

        confidence_score = min(
            1.0,
            total_evidence_weight / cls.MIN_INDEPENDENT_EVIDENCE_FOR_FULL_CONFIDENCE,
        )
        confidence_score = round(max(0.0, min(1.0, confidence_score)), 4)

        distinct_q_count = len(question_attempt_counts)

        # Check sufficiency
        if total_evidence_weight == 0.0:
            sufficiency = SufficiencyStatus.NO_EVIDENCE
        elif (
            confidence_score >= cls.CONFIDENCE_THRESHOLD
            and distinct_q_count >= cls.MIN_DISTINCT_QUESTIONS_FOR_SUFFICIENCY
        ):
            sufficiency = SufficiencyStatus.SUFFICIENT
        else:
            sufficiency = SufficiencyStatus.INSUFFICIENT

        # Conflict Detection:
        # Check whether independent attempts on different questions
        # produce starkly conflicting signals
        is_conflicting = False
        conflict_reasons: list[str] = []

        distinct_initial_ratios = [
            ratios[0] for q, ratios in question_ratios.items() if question_attempt_counts[q] > 0
        ]
        if len(distinct_initial_ratios) >= 2:
            max_r = max(distinct_initial_ratios)
            min_r = min(distinct_initial_ratios)
            if (max_r - min_r) >= cls.CONFLICT_VARIANCE_THRESHOLD:
                is_conflicting = True
                conflict_reasons.append(
                    f"High score discrepancy across distinct questions: min ratio={min_r:.2f}, "
                    f"max ratio={max_r:.2f} (delta >= {cls.CONFLICT_VARIANCE_THRESHOLD:.2f})."
                )

        return EvidenceLedger(
            objective_id=objective_id,
            total_attempts=len(attempts),
            valid_independent_count=valid_independent_count,
            hint_assisted_count=hint_assisted_count,
            repetition_count=repetition_count,
            distinct_questions_count=distinct_q_count,
            total_evidence_weight=round(total_evidence_weight, 3),
            performance_score=performance_score,
            confidence_score=confidence_score,
            sufficiency_status=sufficiency,
            is_conflicting=is_conflicting,
            conflict_reasons=conflict_reasons,
            items=items,
        )

    @classmethod
    def analyze_misconceptions(
        cls,
        ledger: EvidenceLedger,
    ) -> tuple[list[MisconceptionAnalysis], list[MisconceptionAnalysis]]:
        """Extract and categorize error signatures from evidence deductions.

        Rule 2: A single error on an isolated attempt cannot be declared as a
        confirmed misconception. It remains a CANDIDATE_SIGNAL until observed
        across >= 2 distinct items or supported by sufficient evidence.
        """
        # Deductions grouped by reason/signature
        signature_records: dict[str, dict[str, Any]] = {}

        for item in ledger.items:
            for d in item.deductions:
                reason = d.get("reason", "Unspecified Deduction")
                if reason not in signature_records:
                    signature_records[reason] = {
                        "occurrences": 0,
                        "distinct_questions": set(),
                        "sample": d,
                    }
                signature_records[reason]["occurrences"] += 1
                signature_records[reason]["distinct_questions"].add(item.question_id)

        confirmed: list[MisconceptionAnalysis] = []
        candidates: list[MisconceptionAnalysis] = []

        for signature, data in signature_records.items():
            distinct_qs = sorted(data["distinct_questions"])
            count = data["occurrences"]
            sample = data["sample"]

            # Format human-readable description
            extra_info = ""
            if "attributes" in sample:
                extra_info = f" (Attributes: {sample['attributes']})"
            elif "missing_keys" in sample:
                extra_info = f" (Missing: {sample['missing_keys']})"
            desc = f"{signature}{extra_info}"

            # Rule 2: Confirmed requires >= 2 distinct questions or
            # >= 2 occurrences with sufficient evidence
            if len(distinct_qs) >= cls.MIN_OBSERVATIONS_FOR_CONFIRMED_MISCONCEPTION or (
                count >= cls.MIN_OBSERVATIONS_FOR_CONFIRMED_MISCONCEPTION
                and ledger.sufficiency_status == SufficiencyStatus.SUFFICIENT
            ):
                status = MisconceptionStatus.CONFIRMED_MISCONCEPTION
                confirmed.append(
                    MisconceptionAnalysis(
                        signature=signature,
                        description=desc,
                        occurrence_count=count,
                        status=status,
                        distinct_questions=distinct_qs,
                        sample_deduction=sample,
                    )
                )
            else:
                status = MisconceptionStatus.CANDIDATE_SIGNAL
                candidates.append(
                    MisconceptionAnalysis(
                        signature=signature,
                        description=desc,
                        occurrence_count=count,
                        status=status,
                        distinct_questions=distinct_qs,
                        sample_deduction=sample,
                    )
                )

        return (confirmed, candidates)

    @classmethod
    def evaluate_diagnosis(
        cls,
        objective: LearningObjective,
        attempts: list[Attempt],
        prerequisite_diagnoses: dict[str, "BoundedDiagnosticOutcome"] | None = None,
    ) -> BoundedDiagnosticOutcome:
        """Compute authoritative bounded diagnostic outcome for an objective."""
        prerequisite_diagnoses = prerequisite_diagnoses or {}
        applied_rules: list[str] = []

        # 1. Compile audited Evidence Ledger
        ledger = cls.compile_evidence_ledger(objective.id, attempts)
        applied_rules.append("Rule 1: Performance-Confidence Decoupling (Pk vs Ck).")

        if ledger.repetition_count > 0:
            applied_rules.append(
                f"Rule 3: Non-Duplicate Evidence (discounted {ledger.repetition_count} repeat(s))."
            )
        if ledger.hint_assisted_count > 0:
            applied_rules.append(
                f"Rule 4: Hint Degradation (Whint={cls.HINT_EVIDENCE_WEIGHT} "
                f"on {ledger.hint_assisted_count} attempt(s))."
            )

        # 2. Extract Misconceptions
        confirmed_misc, candidate_misc = cls.analyze_misconceptions(ledger)
        if candidate_misc:
            applied_rules.append(
                f"Rule 2: Non-Catastrophic Diagnosis ({len(candidate_misc)} "
                "candidate signal(s) bounded without false weakness declaration)."
            )

        # 3. Analyze Prerequisite Hypotheses (Rule 5)
        prereq_traces: list[PrerequisiteDiagnosticTrace] = []
        all_prereqs_satisfied = True
        prereq_gap_identified = False
        prereq_gap_details: list[str] = []

        for p_ref in objective.prerequisite_objective_ids:
            p_diag = prerequisite_diagnoses.get(p_ref)
            if not p_diag:
                # Prerequisite is untested or missing
                all_prereqs_satisfied = False
                prereq_traces.append(
                    PrerequisiteDiagnosticTrace(
                        prerequisite_ref=p_ref,
                        prerequisite_id=None,
                        prerequisite_code=p_ref,
                        diagnostic_status=DiagnosticStatus.UNTESTED,
                        confidence_score=0.0,
                        is_satisfied=False,
                        gap_hypothesis="Prerequisite untested in current scope.",
                    )
                )
                prereq_gap_identified = True
                prereq_gap_details.append(f"Prerequisite '{p_ref}' is untested.")
            elif p_diag.diagnostic_status in (
                DiagnosticStatus.DEMONSTRATED_WEAKNESS,
                DiagnosticStatus.INSUFFICIENT_EVIDENCE,
                DiagnosticStatus.UNTESTED,
            ):
                all_prereqs_satisfied = False
                prereq_traces.append(
                    PrerequisiteDiagnosticTrace(
                        prerequisite_ref=p_ref,
                        prerequisite_id=p_diag.objective_id,
                        prerequisite_code=p_diag.objective_code,
                        diagnostic_status=p_diag.diagnostic_status,
                        confidence_score=p_diag.confidence_score,
                        is_satisfied=False,
                        gap_hypothesis=(
                            f"Prerequisite '{p_diag.objective_code}' has status "
                            f"'{p_diag.diagnostic_status.value}' (C={p_diag.confidence_score:.2f})."
                        ),
                    )
                )
                prereq_gap_identified = True
                prereq_gap_details.append(
                    f"Prerequisite '{p_diag.objective_code}' status: "
                    f"'{p_diag.diagnostic_status.value}'."
                )
            else:
                prereq_traces.append(
                    PrerequisiteDiagnosticTrace(
                        prerequisite_ref=p_ref,
                        prerequisite_id=p_diag.objective_id,
                        prerequisite_code=p_diag.objective_code,
                        diagnostic_status=p_diag.diagnostic_status,
                        confidence_score=p_diag.confidence_score,
                        is_satisfied=True,
                        gap_hypothesis=None,
                    )
                )

        applied_rules.append(
            "Rule 5: Hypothetical Prerequisites (independent prerequisite causal evaluation)."
        )

        # 4. Determine Diagnostic Status
        if ledger.sufficiency_status == SufficiencyStatus.NO_EVIDENCE:
            diagnostic_status = DiagnosticStatus.UNTESTED
        elif ledger.is_conflicting:
            diagnostic_status = DiagnosticStatus.CONFLICTING_EVIDENCE
        elif ledger.sufficiency_status == SufficiencyStatus.INSUFFICIENT:
            # Rule 2: Single failure or sparse evidence CANNOT declare weakness or mastery
            diagnostic_status = DiagnosticStatus.INSUFFICIENT_EVIDENCE
        elif ledger.performance_score >= cls.MASTERY_PERFORMANCE_THRESHOLD:
            diagnostic_status = DiagnosticStatus.MASTERED
        elif ledger.performance_score >= cls.PASSING_PERFORMANCE_THRESHOLD:
            diagnostic_status = DiagnosticStatus.DEVELOPING
        else:
            diagnostic_status = DiagnosticStatus.DEMONSTRATED_WEAKNESS

        # 5. Root Cause Attribution
        root_cause: str | None = None
        if diagnostic_status == DiagnosticStatus.DEMONSTRATED_WEAKNESS:
            if prereq_gap_identified:
                root_cause = (
                    "PREREQUISITE_HYPOTHESIS_DEFICIT: Objective weakness correlates with "
                    f"unresolved prerequisites ({', '.join(prereq_gap_details)})."
                )
            else:
                root_cause = (
                    "ISOLATED_CONCEPT_GAP: All prerequisites are satisfied; weakness is "
                    "localized strictly to this objective's core mechanics."
                )
        elif diagnostic_status == DiagnosticStatus.INSUFFICIENT_EVIDENCE:
            root_cause = (
                "EVIDENCE_INSUFFICIENT: Inconclusive data prevents diagnostic classification."
            )
        elif diagnostic_status == DiagnosticStatus.CONFLICTING_EVIDENCE:
            root_cause = f"CONFLICTING_SIGNALS: {'; '.join(ledger.conflict_reasons)}"

        # 6. Action Recommendation & Recovery Routing (Rule 7)
        # Check for persistent failure or exhaustion
        failed_count = sum(1 for item in ledger.items if not item.is_correct)
        if failed_count >= 4 and ledger.performance_score < 0.40:
            # Rule 7: Recovery Routing
            recommended_action = DiagnosticAction.GROUNDED_REVISION
            applied_rules.append(
                "Rule 7: Recovery Routing (persistent failure routes to grounded revision)."
            )
        elif not all_prereqs_satisfied and (
            diagnostic_status in (DiagnosticStatus.DEMONSTRATED_WEAKNESS, DiagnosticStatus.UNTESTED)
        ):
            recommended_action = DiagnosticAction.RECOMMEND_PREREQUISITE_REMEDIATION
        elif diagnostic_status in (
            DiagnosticStatus.UNTESTED,
            DiagnosticStatus.INSUFFICIENT_EVIDENCE,
        ):
            recommended_action = DiagnosticAction.RECOMMEND_DIAGNOSTIC_PROBE
        elif diagnostic_status == DiagnosticStatus.CONFLICTING_EVIDENCE:
            recommended_action = DiagnosticAction.RECOMMEND_DIAGNOSTIC_PROBE
        elif diagnostic_status == DiagnosticStatus.DEMONSTRATED_WEAKNESS:
            recommended_action = DiagnosticAction.RECOMMEND_TARGETED_PRACTICE
        elif diagnostic_status == DiagnosticStatus.DEVELOPING:
            recommended_action = DiagnosticAction.RECOMMEND_TARGETED_PRACTICE
        else:
            recommended_action = DiagnosticAction.READY_FOR_ADVANCEMENT

        # 7. Traceable Rationale Assembly
        rationale = (
            f"Objective '{objective.code}' evaluated with {ledger.total_attempts} total attempt(s) "
            f"({ledger.distinct_questions_count} distinct question(s)). "
            f"P={ledger.performance_score:.2f}, C={ledger.confidence_score:.2f} "
            f"(Sufficiency: {ledger.sufficiency_status.value}). "
            f"Diagnostic status assigned: '{diagnostic_status.value}'. "
        )
        if root_cause:
            rationale += f"Attribution: {root_cause} "
        if confirmed_misc:
            rationale += f"Confirmed misconceptions: {len(confirmed_misc)}. "
        if candidate_misc:
            rationale += f"Candidate unverified signals: {len(candidate_misc)}. "

        return BoundedDiagnosticOutcome(
            objective_id=objective.id,
            objective_code=objective.code,
            diagnostic_status=diagnostic_status,
            performance_score=ledger.performance_score,
            confidence_score=ledger.confidence_score,
            sufficiency_status=ledger.sufficiency_status,
            evidence_ledger=ledger,
            confirmed_misconceptions=confirmed_misc,
            candidate_signals=candidate_misc,
            prerequisites_satisfied=all_prereqs_satisfied,
            prerequisite_traces=prereq_traces,
            root_cause_attribution=root_cause,
            recommended_action=recommended_action,
            applied_rules=applied_rules,
            traceable_rationale=rationale,
        )
