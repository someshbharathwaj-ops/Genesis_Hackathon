"""Evidence Representation and Bounded Diagnosis Service.

Provides authoritative diagnostic evaluations and session plans respecting
frozen rules and session budget limits.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.models.attempt import Attempt
from app.models.curriculum import LearningObjective
from app.models.question import VerificationStatus
from app.modules.adaptive_learning.diagnosis_engine import (
    BoundedDiagnosisEngine,
    BoundedDiagnosticOutcome,
    DiagnosticStatus,
)
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.question_repo import QuestionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.diagnosis import (
    CourseDiagnosticSummaryResponse,
    DiagnosticSessionPlanResponse,
    EvidenceItemResponse,
    EvidenceLedgerResponse,
    MisconceptionResponse,
    ObjectiveDiagnosticResponse,
    PrerequisiteTraceResponse,
    RecommendedQuestionItem,
)


class DiagnosisService:
    """Service orchestrating evidence representation, bounded diagnosis, and session routing."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.course_repo = CourseRepository(session)
        self.topic_repo = TopicRepository(session)
        self.lo_repo = LearningObjectiveRepository(session)
        self.attempt_repo = AttemptRepository(session)
        self.question_repo = QuestionRepository(session)

    @staticmethod
    def _outcome_to_response(outcome: BoundedDiagnosticOutcome) -> ObjectiveDiagnosticResponse:
        ledger = outcome.evidence_ledger
        items_resp = [
            EvidenceItemResponse(
                attempt_id=i.attempt_id,
                question_id=i.question_id,
                assessment_context=i.assessment_context,
                score_ratio=i.score_ratio,
                is_correct=i.is_correct,
                is_hint_assisted=i.is_hint_assisted,
                hint_count=i.hint_count,
                repetition_index=i.repetition_index,
                effective_weight=i.effective_weight,
                validity=i.validity,
                deductions=i.deductions,
                submitted_at=i.submitted_at,
            )
            for i in ledger.items
        ]
        ledger_resp = EvidenceLedgerResponse(
            objective_id=ledger.objective_id,
            total_attempts=ledger.total_attempts,
            valid_independent_count=ledger.valid_independent_count,
            hint_assisted_count=ledger.hint_assisted_count,
            repetition_count=ledger.repetition_count,
            distinct_questions_count=ledger.distinct_questions_count,
            total_evidence_weight=ledger.total_evidence_weight,
            performance_score=ledger.performance_score,
            confidence_score=ledger.confidence_score,
            sufficiency_status=ledger.sufficiency_status,
            is_conflicting=ledger.is_conflicting,
            conflict_reasons=ledger.conflict_reasons,
            items=items_resp,
        )
        confirmed_resp = [
            MisconceptionResponse(
                signature=m.signature,
                description=m.description,
                occurrence_count=m.occurrence_count,
                status=m.status,
                distinct_questions=m.distinct_questions,
                sample_deduction=m.sample_deduction,
            )
            for m in outcome.confirmed_misconceptions
        ]
        candidates_resp = [
            MisconceptionResponse(
                signature=m.signature,
                description=m.description,
                occurrence_count=m.occurrence_count,
                status=m.status,
                distinct_questions=m.distinct_questions,
                sample_deduction=m.sample_deduction,
            )
            for m in outcome.candidate_signals
        ]
        traces_resp = [
            PrerequisiteTraceResponse(
                prerequisite_ref=t.prerequisite_ref,
                prerequisite_id=t.prerequisite_id,
                prerequisite_code=t.prerequisite_code,
                diagnostic_status=t.diagnostic_status,
                confidence_score=t.confidence_score,
                is_satisfied=t.is_satisfied,
                gap_hypothesis=t.gap_hypothesis,
            )
            for t in outcome.prerequisite_traces
        ]

        return ObjectiveDiagnosticResponse(
            objective_id=outcome.objective_id,
            objective_code=outcome.objective_code,
            diagnostic_status=outcome.diagnostic_status,
            performance_score=outcome.performance_score,
            confidence_score=outcome.confidence_score,
            sufficiency_status=outcome.sufficiency_status,
            evidence_ledger=ledger_resp,
            confirmed_misconceptions=confirmed_resp,
            candidate_signals=candidates_resp,
            prerequisites_satisfied=outcome.prerequisites_satisfied,
            prerequisite_traces=traces_resp,
            root_cause_attribution=outcome.root_cause_attribution,
            recommended_action=outcome.recommended_action,
            applied_rules=outcome.applied_rules,
            traceable_rationale=outcome.traceable_rationale,
        )

    async def get_objective_diagnosis(
        self, student_id: str, objective_id: str
    ) -> ObjectiveDiagnosticResponse:
        """Evaluate granular bounded diagnosis for a single learning objective."""
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        lo = await self.lo_repo.get_by_id(objective_id)
        if not lo:
            raise ResourceNotFoundError("LearningObjective", objective_id)

        # 1. Fetch attempts for this objective
        attempts = await self.attempt_repo.list_by_student_for_objectives(
            student_id, [objective_id]
        )

        # 2. Fetch prerequisite diagnoses
        topic = await self.topic_repo.get_by_id(lo.topic_id)
        prereq_diagnoses: dict[str, BoundedDiagnosticOutcome] = {}
        if topic:
            topics = await self.topic_repo.list_by_course(topic.course_id)
            course_los_by_id = {o.id: o for t in topics for o in t.objectives}
            course_los_by_code = {o.code: o for t in topics for o in t.objectives}

            for p_ref in lo.prerequisite_objective_ids:
                p_lo = course_los_by_id.get(p_ref) or course_los_by_code.get(p_ref)
                if p_lo:
                    p_attempts = await self.attempt_repo.list_by_student_for_objectives(
                        student_id, [p_lo.id]
                    )
                    p_outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
                        objective=p_lo,
                        attempts=p_attempts,
                    )
                    prereq_diagnoses[p_ref] = p_outcome
                    prereq_diagnoses[p_lo.id] = p_outcome
                    prereq_diagnoses[p_lo.code] = p_outcome

        # 3. Evaluate diagnosis
        outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
            objective=lo,
            attempts=attempts,
            prerequisite_diagnoses=prereq_diagnoses,
        )
        return self._outcome_to_response(outcome)

    async def get_course_diagnosis(
        self, student_id: str, course_id: str
    ) -> CourseDiagnosticSummaryResponse:
        """Evaluate course-wide diagnostic summary and root-cause gaps in topological order."""
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        topics = await self.topic_repo.list_by_course(course_id)
        objectives: list[LearningObjective] = []
        for t in topics:
            objectives.extend(t.objectives)

        if not objectives:
            return CourseDiagnosticSummaryResponse(
                student_id=student_id,
                course_id=course_id,
                total_objectives=0,
                mastered_count=0,
                developing_count=0,
                demonstrated_weakness_count=0,
                insufficient_evidence_count=0,
                untested_count=0,
                conflicting_count=0,
                average_performance=0.0,
                average_confidence=0.0,
                identified_root_cause_gaps=[],
                objectives=[],
            )

        objective_ids = [lo.id for lo in objectives]

        # Fetch all student attempts for course objectives
        attempts = await self.attempt_repo.list_by_student_for_objectives(student_id, objective_ids)

        q_ids = {a.question_id for a in attempts}
        q_to_lo: dict[str, str] = {}
        for qid in q_ids:
            q = await self.question_repo.get_by_id(qid)
            if q:
                q_to_lo[qid] = q.objective_id

        attempts_by_lo: dict[str, list[Attempt]] = {lo_id: [] for lo_id in objective_ids}
        for a in attempts:
            lo_id = q_to_lo.get(a.question_id)
            if lo_id and lo_id in attempts_by_lo:
                attempts_by_lo[lo_id].append(a)

        # Topologically evaluate objectives
        outcomes_by_ref: dict[str, BoundedDiagnosticOutcome] = {}
        outcome_responses: list[ObjectiveDiagnosticResponse] = []
        identified_root_cause_gaps: list[str] = []

        unprocessed = list(objectives)
        max_iterations = len(objectives) + 1
        iteration = 0

        while unprocessed and iteration < max_iterations:
            iteration += 1
            progress = False
            for lo in list(unprocessed):
                prereqs = lo.prerequisite_objective_ids
                can_process = all(
                    (p in outcomes_by_ref)
                    or (
                        p not in [o.code for o in objectives]
                        and p not in [o.id for o in objectives]
                    )
                    for p in prereqs
                )
                if can_process or iteration == max_iterations:
                    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
                        objective=lo,
                        attempts=attempts_by_lo[lo.id],
                        prerequisite_diagnoses=outcomes_by_ref,
                    )
                    outcomes_by_ref[lo.id] = outcome
                    outcomes_by_ref[lo.code] = outcome
                    outcome_responses.append(self._outcome_to_response(outcome))
                    if outcome.root_cause_attribution:
                        identified_root_cause_gaps.append(
                            f"[{lo.code}] {outcome.root_cause_attribution}"
                        )
                    unprocessed.remove(lo)
                    progress = True
            if not progress:
                for lo in list(unprocessed):
                    outcome = BoundedDiagnosisEngine.evaluate_diagnosis(
                        objective=lo,
                        attempts=attempts_by_lo[lo.id],
                        prerequisite_diagnoses=outcomes_by_ref,
                    )
                    outcomes_by_ref[lo.id] = outcome
                    outcomes_by_ref[lo.code] = outcome
                    outcome_responses.append(self._outcome_to_response(outcome))
                    if outcome.root_cause_attribution:
                        identified_root_cause_gaps.append(
                            f"[{lo.code}] {outcome.root_cause_attribution}"
                        )
                    unprocessed.remove(lo)

        # Summary statistics
        mastered_c = sum(
            1 for o in outcome_responses if o.diagnostic_status == DiagnosticStatus.MASTERED
        )
        developing_c = sum(
            1 for o in outcome_responses if o.diagnostic_status == DiagnosticStatus.DEVELOPING
        )
        weakness_c = sum(
            1
            for o in outcome_responses
            if o.diagnostic_status == DiagnosticStatus.DEMONSTRATED_WEAKNESS
        )
        insufficient_c = sum(
            1
            for o in outcome_responses
            if o.diagnostic_status == DiagnosticStatus.INSUFFICIENT_EVIDENCE
        )
        untested_c = sum(
            1 for o in outcome_responses if o.diagnostic_status == DiagnosticStatus.UNTESTED
        )
        conflicting_c = sum(
            1
            for o in outcome_responses
            if o.diagnostic_status == DiagnosticStatus.CONFLICTING_EVIDENCE
        )

        avg_perf = (
            round(sum(o.performance_score for o in outcome_responses) / len(outcome_responses), 4)
            if outcome_responses
            else 0.0
        )
        avg_conf = (
            round(sum(o.confidence_score for o in outcome_responses) / len(outcome_responses), 4)
            if outcome_responses
            else 0.0
        )

        return CourseDiagnosticSummaryResponse(
            student_id=student_id,
            course_id=course_id,
            total_objectives=len(outcome_responses),
            mastered_count=mastered_c,
            developing_count=developing_c,
            demonstrated_weakness_count=weakness_c,
            insufficient_evidence_count=insufficient_c,
            untested_count=untested_c,
            conflicting_count=conflicting_c,
            average_performance=avg_perf,
            average_confidence=avg_conf,
            identified_root_cause_gaps=identified_root_cause_gaps,
            objectives=outcome_responses,
        )

    async def create_session_plan(
        self,
        student_id: str,
        course_id: str,
        target_objective_id: str | None = None,
    ) -> DiagnosticSessionPlanResponse:
        """Create a bounded diagnostic session plan (strictly <= 5 questions).

        Selection prioritization:
        1. If target objective is specified, prioritize untested/weak prerequisites.
        2. Questions addressing candidate unverified error signals.
        3. Introductory/verified questions on unassessed or insufficient objectives.
        """
        course_diag = await self.get_course_diagnosis(student_id, course_id)

        target_obj: ObjectiveDiagnosticResponse | None = None
        if target_objective_id:
            target_obj = next(
                (o for o in course_diag.objectives if o.objective_id == target_objective_id),
                None,
            )

        # Objectives to prioritize
        priority_lo_ids: list[tuple[str, str]] = []  # (objective_id, reason)

        if target_obj:
            # Check prerequisites first
            for trace in target_obj.prerequisite_traces:
                if not trace.is_satisfied and trace.prerequisite_id:
                    priority_lo_ids.append(
                        (
                            trace.prerequisite_id,
                            f"Prerequisite probe for {target_obj.objective_code}",
                        )
                    )
            # Add target objective itself
            priority_lo_ids.append(
                (target_obj.objective_id, f"Target diagnosis for {target_obj.objective_code}")
            )

        # Add course-level priority objectives (weakness or insufficient evidence)
        for obj in course_diag.objectives:
            if obj.objective_id not in [p[0] for p in priority_lo_ids]:
                if obj.diagnostic_status in (
                    DiagnosticStatus.DEMONSTRATED_WEAKNESS,
                    DiagnosticStatus.INSUFFICIENT_EVIDENCE,
                    DiagnosticStatus.UNTESTED,
                    DiagnosticStatus.CONFLICTING_EVIDENCE,
                ):
                    priority_lo_ids.append(
                        (obj.objective_id, f"Course diagnosis for {obj.objective_code}")
                    )

        recommended_questions: list[RecommendedQuestionItem] = []
        already_selected_q_ids: set[str] = set()

        for lo_id, reason in priority_lo_ids:
            if (
                len(recommended_questions)
                >= BoundedDiagnosisEngine.MAX_DIAGNOSTIC_SESSION_QUESTIONS
            ):
                break

            questions = await self.question_repo.list_by_objective(lo_id, only_active=True)
            for q in questions:
                if (
                    len(recommended_questions)
                    >= BoundedDiagnosisEngine.MAX_DIAGNOSTIC_SESSION_QUESTIONS
                ):
                    break
                if q.id in already_selected_q_ids:
                    continue

                # Ensure question has a verified version
                verified_version = next(
                    (v for v in q.versions if v.verification_status == VerificationStatus.VERIFIED),
                    None,
                )
                if not verified_version:
                    continue

                # Fetch objective code
                lo = await self.lo_repo.get_by_id(lo_id)
                lo_code = lo.code if lo else lo_id

                recommended_questions.append(
                    RecommendedQuestionItem(
                        question_id=q.id,
                        title=q.title,
                        objective_id=lo_id,
                        objective_code=lo_code,
                        difficulty=verified_version.difficulty.value,
                        priority_reason=reason,
                    )
                )
                already_selected_q_ids.add(q.id)

        session_rationale = (
            f"Bounded session planned with {len(recommended_questions)} question(s) "
            f"(bounded by ceiling <= {BoundedDiagnosisEngine.MAX_DIAGNOSTIC_SESSION_QUESTIONS}). "
            "Prioritized targeted probes for prerequisites and unverified evidence."
        )

        return DiagnosticSessionPlanResponse(
            student_id=student_id,
            course_id=course_id,
            target_objective_id=target_objective_id,
            max_session_questions=BoundedDiagnosisEngine.MAX_DIAGNOSTIC_SESSION_QUESTIONS,
            recommended_questions=recommended_questions,
            session_rationale=session_rationale,
        )
