"""Spaced Retention Scheduling service coordinating persisted attempts and review queues."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ResourceNotFoundError
from app.models.attempt import Attempt
from app.models.curriculum import LearningObjective
from app.modules.adaptive_learning.mastery_engine import (
    MasteryEngine,
    ObjectiveMasteryProfile,
)
from app.modules.adaptive_learning.scheduling_engine import (
    RetentionScheduleItem,
    SchedulingEngine,
)
from app.repositories.attempt_repo import AttemptRepository
from app.repositories.course_repo import (
    CourseRepository,
    LearningObjectiveRepository,
    TopicRepository,
)
from app.repositories.question_repo import QuestionRepository
from app.repositories.user_repo import UserRepository
from app.schemas.scheduling import (
    RetentionItemSchema,
    RetentionSessionPlanResponse,
    ReviewQueueResponse,
)


class SchedulingService:
    """Service orchestrating deterministic spaced retention review queues and session planning."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.course_repo = CourseRepository(session)
        self.topic_repo = TopicRepository(session)
        self.lo_repo = LearningObjectiveRepository(session)
        self.attempt_repo = AttemptRepository(session)
        self.question_repo = QuestionRepository(session)

    async def get_student_review_queue(
        self,
        course_id: str,
        student_id: str,
        as_of_time: datetime | None = None,
        cooldown_seconds: float | None = None,
    ) -> ReviewQueueResponse:
        """Calculate the student's authoritative spaced retention review queue for a course."""
        student = await self.user_repo.get_by_id(student_id)
        if not student:
            raise ResourceNotFoundError("User", student_id)

        course = await self.course_repo.get_by_id(course_id)
        if not course:
            raise ResourceNotFoundError("Course", course_id)

        now = as_of_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        # 1. Fetch course hierarchy
        topics = await self.topic_repo.list_by_course(course_id)
        objectives: list[LearningObjective] = []
        for t in topics:
            objectives.extend(t.objectives)

        if not objectives:
            return ReviewQueueResponse(
                student_id=student_id,
                course_id=course_id,
                as_of_time=now,
                total_objectives_evaluated=0,
                overdue_count=0,
                due_count=0,
                working_memory_locked_count=0,
                items=[],
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

        # 3. Compute deterministic mastery profiles in topological order
        profiles_by_ref: dict[str, ObjectiveMasteryProfile] = {}
        unprocessed = list(objectives)
        max_iterations = len(objectives) + 1
        iteration = 0

        while unprocessed and iteration < max_iterations:
            iteration += 1
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
                    unprocessed.remove(lo)

        # 4. Compute retention schedule items using SchedulingEngine
        schedule_items: list[RetentionScheduleItem] = []
        for lo in objectives:
            prof = profiles_by_ref[lo.id]
            lo_attempts = attempts_by_lo[lo.id]
            sched_item = SchedulingEngine.compute_objective_schedule(
                objective=lo,
                attempts=lo_attempts,
                mastery_profile=prof,
                as_of_time=now,
                cooldown_seconds=cooldown_seconds,
            )
            schedule_items.append(sched_item)

        # 5. Build prioritized queue
        queue = SchedulingEngine.build_review_queue(
            student_id=student_id,
            course_id=course_id,
            items=schedule_items,
            as_of_time=now,
        )

        return ReviewQueueResponse(
            student_id=queue.student_id,
            course_id=queue.course_id,
            as_of_time=queue.as_of_time,
            total_objectives_evaluated=queue.total_objectives_evaluated,
            overdue_count=queue.overdue_count,
            due_count=queue.due_count,
            working_memory_locked_count=queue.working_memory_locked_count,
            items=[self._map_to_schema(it) for it in queue.items],
        )

    async def plan_retention_session(
        self,
        course_id: str,
        student_id: str,
        max_items: int = 5,
        as_of_time: datetime | None = None,
        cooldown_seconds: float | None = None,
    ) -> RetentionSessionPlanResponse:
        """Plan a bounded spaced retention review session for a student."""
        queue_resp = await self.get_student_review_queue(
            course_id=course_id,
            student_id=student_id,
            as_of_time=as_of_time,
            cooldown_seconds=cooldown_seconds,
        )

        # Reconstruct domain queue to utilize domain planning logic
        domain_items = [
            RetentionScheduleItem(
                objective_id=it.objective_id,
                objective_code=it.objective_code,
                objective_title=it.objective_title,
                mastery_state=it.mastery_state,
                performance_score=it.performance_score,
                confidence_score=it.confidence_score,
                last_attempt_at=it.last_attempt_at,
                elapsed_hours=it.elapsed_hours,
                in_working_memory=it.in_working_memory,
                retention_eligible=it.retention_eligible,
                interval_days=it.interval_days,
                next_review_due=it.next_review_due,
                retention_stability_days=it.retention_stability_days,
                estimated_retention=it.estimated_retention,
                urgency_score=it.urgency_score,
                urgency_classification=it.urgency_classification,
                recommended_action=it.recommended_action,
                metadata=it.metadata,
            )
            for it in queue_resp.items
        ]

        queue = SchedulingEngine.build_review_queue(
            student_id=student_id,
            course_id=course_id,
            items=domain_items,
            as_of_time=queue_resp.as_of_time,
        )

        plan = SchedulingEngine.plan_retention_session(
            queue=queue,
            max_session_items=max_items,
        )

        return RetentionSessionPlanResponse(
            student_id=plan.student_id,
            course_id=plan.course_id,
            as_of_time=plan.as_of_time,
            context=plan.context,
            total_items=plan.total_items,
            reason=plan.reason,
            planned_items=[self._map_to_schema(it) for it in plan.planned_items],
        )

    def _map_to_schema(self, item: RetentionScheduleItem) -> RetentionItemSchema:
        return RetentionItemSchema(
            objective_id=item.objective_id,
            objective_code=item.objective_code,
            objective_title=item.objective_title,
            mastery_state=item.mastery_state,
            performance_score=item.performance_score,
            confidence_score=item.confidence_score,
            last_attempt_at=item.last_attempt_at,
            elapsed_hours=item.elapsed_hours,
            in_working_memory=item.in_working_memory,
            retention_eligible=item.retention_eligible,
            interval_days=item.interval_days,
            next_review_due=item.next_review_due,
            retention_stability_days=item.retention_stability_days,
            estimated_retention=item.estimated_retention,
            urgency_score=item.urgency_score,
            urgency_classification=item.urgency_classification,
            recommended_action=item.recommended_action,
            metadata=item.metadata,
        )
