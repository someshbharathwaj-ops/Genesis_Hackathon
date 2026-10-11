"""Mastery calculation service coordinating attempt ledgers and curriculum DAGs."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.models.attempt import Attempt
from app.models.curriculum import LearningObjective
from app.modules.adaptive_learning.mastery_engine import (
    MasteryEngine,
    MasteryState,
    ObjectiveMasteryProfile,
)
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.question_repo import QuestionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.mastery import CourseMasterySummaryResponse, ObjectiveMasteryResponse


class MasteryService:
    """Service providing authoritative mastery profiles."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.course_repo = CourseRepository(session)
        self.topic_repo = TopicRepository(session)
        self.lo_repo = LearningObjectiveRepository(session)
        self.attempt_repo = AttemptRepository(session)
        self.question_repo = QuestionRepository(session)

    async def get_course_mastery(
        self, student_id: str, course_id: str
    ) -> CourseMasterySummaryResponse:
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        # 1. Fetch all topics and objectives in course
        topics = await self.topic_repo.list_by_course(course_id)
        objectives: list[LearningObjective] = []
        for t in topics:
            objectives.extend(t.objectives)

        if not objectives:
            return CourseMasterySummaryResponse(
                student_id=student_id,
                course_id=course_id,
                total_objectives=0,
                mastered_count=0,
                developing_count=0,
                needs_remediation_count=0,
                untested_count=0,
                average_performance=0.0,
                average_confidence=0.0,
                objectives=[],
            )

        objective_ids = [lo.id for lo in objectives]

        # 2. Fetch all student attempts for questions belonging to these objectives
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

        # 3. Compute mastery in topological order so prerequisites are evaluated first
        profiles_by_ref: dict[str, ObjectiveMasteryProfile] = {}
        profile_list: list[ObjectiveMasteryResponse] = []

        unprocessed = list(objectives)
        max_iterations = len(objectives) + 1
        iteration = 0

        while unprocessed and iteration < max_iterations:
            iteration += 1
            progress = False
            for lo in list(unprocessed):
                prereqs = lo.prerequisite_objective_ids
                can_process = all(
                    (p in profiles_by_ref)
                    or (
                        p not in [o.code for o in objectives]
                        and p not in [o.id for o in objectives]
                    )
                    for p in prereqs
                )
                if can_process or iteration == max_iterations:
                    prof = MasteryEngine.compute_objective_mastery(
                        objective=lo,
                        attempts=attempts_by_lo[lo.id],
                        prerequisite_profiles=profiles_by_ref,
                    )
                    profiles_by_ref[lo.id] = prof
                    profiles_by_ref[lo.code] = prof
                    profile_list.append(
                        ObjectiveMasteryResponse(
                            objective_id=prof.objective_id,
                            objective_code=prof.objective_code,
                            performance_score=prof.performance_score,
                            confidence_score=prof.confidence_score,
                            mastery_state=prof.mastery_state,
                            prerequisites_satisfied=prof.prerequisites_satisfied,
                            blocked_by_prerequisites=prof.blocked_by_prerequisites,
                            total_attempts=prof.total_attempts,
                            distinct_questions_attempted=prof.distinct_questions_attempted,
                            unassisted_correct_count=prof.unassisted_correct_count,
                            hint_assisted_count=prof.hint_assisted_count,
                            details=prof.details,
                        )
                    )
                    unprocessed.remove(lo)
                    progress = True
            if not progress:
                for lo in list(unprocessed):
                    prof = MasteryEngine.compute_objective_mastery(
                        objective=lo,
                        attempts=attempts_by_lo[lo.id],
                        prerequisite_profiles=profiles_by_ref,
                    )
                    profiles_by_ref[lo.id] = prof
                    profiles_by_ref[lo.code] = prof
                    profile_list.append(
                        ObjectiveMasteryResponse(
                            objective_id=prof.objective_id,
                            objective_code=prof.objective_code,
                            performance_score=prof.performance_score,
                            confidence_score=prof.confidence_score,
                            mastery_state=prof.mastery_state,
                            prerequisites_satisfied=prof.prerequisites_satisfied,
                            blocked_by_prerequisites=prof.blocked_by_prerequisites,
                            total_attempts=prof.total_attempts,
                            distinct_questions_attempted=prof.distinct_questions_attempted,
                            unassisted_correct_count=prof.unassisted_correct_count,
                            hint_assisted_count=prof.hint_assisted_count,
                            details=prof.details,
                        )
                    )
                    unprocessed.remove(lo)

        # 4. Aggregations
        mastered_count = sum(1 for p in profile_list if p.mastery_state == MasteryState.MASTERED)
        developing_count = sum(
            1 for p in profile_list if p.mastery_state == MasteryState.DEVELOPING
        )
        remediation_count = sum(
            1 for p in profile_list if p.mastery_state == MasteryState.NEEDS_REMEDIATION
        )
        untested_count = sum(
            1
            for p in profile_list
            if p.mastery_state in (MasteryState.UNTESTED, MasteryState.INSUFFICIENT_EVIDENCE)
        )

        avg_perf = (
            round(sum(p.performance_score for p in profile_list) / len(profile_list), 4)
            if profile_list
            else 0.0
        )
        avg_conf = (
            round(sum(p.confidence_score for p in profile_list) / len(profile_list), 4)
            if profile_list
            else 0.0
        )

        return CourseMasterySummaryResponse(
            student_id=student_id,
            course_id=course_id,
            total_objectives=len(profile_list),
            mastered_count=mastered_count,
            developing_count=developing_count,
            needs_remediation_count=remediation_count,
            untested_count=untested_count,
            average_performance=avg_perf,
            average_confidence=avg_conf,
            objectives=profile_list,
        )

    async def get_objective_mastery(
        self, student_id: str, objective_id: str
    ) -> ObjectiveMasteryResponse:
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        lo = await self.lo_repo.get_by_id(objective_id)
        if not lo:
            raise ResourceNotFoundError("LearningObjective", objective_id)

        # Fetch attempts for this objective
        attempts = await self.attempt_repo.list_by_student_for_objectives(
            student_id, [objective_id]
        )

        # Fetch topic to find course
        topic = await self.topic_repo.get_by_id(lo.topic_id)
        prereq_profiles: dict[str, ObjectiveMasteryProfile] = {}
        if topic:
            topics = await self.topic_repo.list_by_course(topic.course_id)
            course_los = {o.id: o for t in topics for o in t.objectives}
            course_los_by_code = {o.code: o for t in topics for o in t.objectives}

            for p_ref in lo.prerequisite_objective_ids:
                p_lo = course_los.get(p_ref) or course_los_by_code.get(p_ref)
                if p_lo:
                    p_atts = await self.attempt_repo.list_by_student_for_objectives(
                        student_id, [p_lo.id]
                    )
                    p_prof = MasteryEngine.compute_objective_mastery(
                        objective=p_lo,
                        attempts=p_atts,
                    )
                    prereq_profiles[p_ref] = p_prof
                    prereq_profiles[p_lo.code] = p_prof
                    prereq_profiles[p_lo.id] = p_prof

        prof = MasteryEngine.compute_objective_mastery(
            objective=lo,
            attempts=attempts,
            prerequisite_profiles=prereq_profiles,
        )

        return ObjectiveMasteryResponse(
            objective_id=prof.objective_id,
            objective_code=prof.objective_code,
            performance_score=prof.performance_score,
            confidence_score=prof.confidence_score,
            mastery_state=prof.mastery_state,
            prerequisites_satisfied=prof.prerequisites_satisfied,
            blocked_by_prerequisites=prof.blocked_by_prerequisites,
            total_attempts=prof.total_attempts,
            distinct_questions_attempted=prof.distinct_questions_attempted,
            unassisted_correct_count=prof.unassisted_correct_count,
            hint_assisted_count=prof.hint_assisted_count,
            details=prof.details,
        )
