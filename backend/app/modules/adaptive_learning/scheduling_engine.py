"""Deterministic Spaced Retention Scheduling Engine.

Implements Rule 6 (Retention Separation):
"Retesting immediately after review measures working memory, not durable mastery;
spaced review scheduling enforces delayed retention checks."

Responsibilities:
1. Deterministic calculation of retention intervals based on mastery P_k, confidence C_k,
   and consecutive unassisted successes.
2. Enforcement of working memory cooldown (attempts within cooldown window are locked
   out from retention retesting to prevent testing transient recall).
3. Exponential retention stability modeling R(t) = exp(-delta_t / S).
4. Review queue prioritization by retention decay and urgency.
5. Deterministic session planning for retention reviews (AssessmentContext.RETENTION_REVIEW).
"""

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.models.attempt import AssessmentContext, Attempt
from app.models.curriculum import LearningObjective
from app.modules.adaptive_learning.mastery_engine import (
    MasteryState,
    ObjectiveMasteryProfile,
)


class ReviewUrgency(str, Enum):
    """Categorical classification of review urgency."""

    OVERDUE = "overdue"
    DUE = "due"
    UPCOMING = "upcoming"
    COOLDOWN_LOCKED = "cooldown_locked"
    UNTESTED = "untested"


@dataclass
class RetentionScheduleItem:
    """Spaced retention schedule evaluation for a single learning objective."""

    objective_id: str
    objective_code: str
    objective_title: str
    mastery_state: MasteryState
    performance_score: float  # P_k in [0.0, 1.0]
    confidence_score: float  # C_k in [0.0, 1.0]
    last_attempt_at: datetime | None
    elapsed_hours: float
    in_working_memory: bool  # True if elapsed time < cooldown threshold
    retention_eligible: bool  # False if in working memory or untested
    interval_days: float  # Deterministic target spacing interval
    next_review_due: datetime | None
    retention_stability_days: float
    estimated_retention: float  # R(t) in [0.0, 1.0]
    urgency_score: float  # Higher score = higher priority in review queue
    urgency_classification: ReviewUrgency
    recommended_action: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SpacedReviewQueue:
    """Prioritized queue of retention review items for a student."""

    student_id: str
    course_id: str
    as_of_time: datetime
    total_objectives_evaluated: int
    overdue_count: int
    due_count: int
    working_memory_locked_count: int
    items: list[RetentionScheduleItem]


@dataclass
class RetentionSessionPlan:
    """Bounded, ready-to-execute retention review session."""

    student_id: str
    course_id: str
    as_of_time: datetime
    context: AssessmentContext
    planned_items: list[RetentionScheduleItem]
    total_items: int
    reason: str


def _get_attempt_timestamp(attempt: Attempt) -> float:
    ts = attempt.created_at or attempt.submitted_at
    if ts is None:
        return 0.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.timestamp()


class SchedulingEngine:
    """Authoritative deterministic spaced retention scheduling engine."""

    # Default working memory cooldown: 1 hour (3600s)
    DEFAULT_COOLDOWN_SECONDS: float = 3600.0

    # Minimum and maximum intervals in days
    MIN_INTERVAL_DAYS: float = 1.0
    MAX_INTERVAL_DAYS: float = 60.0

    # Base stability multiplier
    BASE_STABILITY_DAYS: float = 2.0

    @classmethod
    def compute_objective_schedule(
        cls,
        objective: LearningObjective,
        attempts: list[Attempt],
        mastery_profile: ObjectiveMasteryProfile,
        as_of_time: datetime | None = None,
        cooldown_seconds: float | None = None,
    ) -> RetentionScheduleItem:
        """Compute the deterministic retention schedule for a single objective."""
        now = as_of_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        cooldown = (
            cooldown_seconds if cooldown_seconds is not None else cls.DEFAULT_COOLDOWN_SECONDS
        )

        # 1. Determine most recent attempt timestamp
        last_attempt_time: datetime | None = None
        consecutive_unassisted_correct = 0

        if attempts:
            sorted_atts = sorted(attempts, key=_get_attempt_timestamp)
            latest = sorted_atts[-1]
            last_attempt_time = latest.created_at or latest.submitted_at
            if last_attempt_time and last_attempt_time.tzinfo is None:
                last_attempt_time = last_attempt_time.replace(tzinfo=UTC)

            # Count trailing consecutive unassisted correct attempts
            for att in reversed(sorted_atts):
                if att.is_correct and not att.is_hint_assisted:
                    consecutive_unassisted_correct += 1
                else:
                    break

        # 2. Check Rule 6: Working Memory Cooldown
        elapsed_seconds: float = 0.0
        elapsed_hours: float = 0.0
        in_working_memory = False

        if last_attempt_time is not None:
            diff = (now - last_attempt_time).total_seconds()
            elapsed_seconds = max(0.0, diff)
            elapsed_hours = round(elapsed_seconds / 3600.0, 2)
            if elapsed_seconds < cooldown:
                in_working_memory = True

        # 3. Handle Untested state
        if not attempts or mastery_profile.mastery_state == MasteryState.UNTESTED:
            return RetentionScheduleItem(
                objective_id=objective.id,
                objective_code=objective.code,
                objective_title=objective.title,
                mastery_state=MasteryState.UNTESTED,
                performance_score=0.0,
                confidence_score=0.0,
                last_attempt_at=None,
                elapsed_hours=0.0,
                in_working_memory=False,
                retention_eligible=False,
                interval_days=0.0,
                next_review_due=now,
                retention_stability_days=0.0,
                estimated_retention=0.0,
                urgency_score=0.5,
                urgency_classification=ReviewUrgency.UNTESTED,
                recommended_action=(
                    "Conduct initial diagnostic probe before scheduling retention review."
                ),
                metadata={"reason": "Objective is untested."},
            )

        # 4. Compute Spaced Repetition Interval (Half-life / Stability)
        p_k = mastery_profile.performance_score
        c_k = mastery_profile.confidence_score

        if mastery_profile.mastery_state == MasteryState.NEEDS_REMEDIATION:
            interval_days = cls.MIN_INTERVAL_DAYS
            stability_days = cls.BASE_STABILITY_DAYS * 0.5
        elif mastery_profile.mastery_state == MasteryState.INSUFFICIENT_EVIDENCE:
            interval_days = cls.MIN_INTERVAL_DAYS
            stability_days = cls.BASE_STABILITY_DAYS * 0.8
        elif mastery_profile.mastery_state == MasteryState.DEVELOPING:
            interval_days = min(
                5.0,
                max(cls.MIN_INTERVAL_DAYS, 2.0 + 2.0 * p_k + 0.5 * consecutive_unassisted_correct),
            )
            stability_days = cls.BASE_STABILITY_DAYS * (1.0 + p_k)
        else:  # MASTERED
            easiness_factor = 1.3 + (0.7 * p_k) + (0.3 * c_k)
            exp_power = min(consecutive_unassisted_correct, 5)
            interval_days = min(
                cls.MAX_INTERVAL_DAYS,
                round(3.0 * math.pow(easiness_factor, max(1, exp_power)), 1),
            )
            stability_days = round(interval_days * (0.8 + 0.4 * c_k), 2)

        interval_days = max(cls.MIN_INTERVAL_DAYS, min(cls.MAX_INTERVAL_DAYS, interval_days))
        stability_days = max(0.5, stability_days)

        # 5. Compute Next Due Date and Exponential Retention Decay
        elapsed_days = elapsed_seconds / 86400.0
        decay_ratio = elapsed_days / stability_days
        estimated_retention = round(math.exp(-min(10.0, decay_ratio)), 4)

        next_due_timestamp = (
            last_attempt_time.timestamp() + (interval_days * 86400.0)
            if last_attempt_time
            else now.timestamp()
        )
        next_review_due = datetime.fromtimestamp(next_due_timestamp, tz=UTC)

        # 6. Evaluate Urgency & Rule 6 Working Memory Lockout
        urgency_score: float
        urgency_classification: ReviewUrgency
        retention_eligible: bool
        action_desc: str

        if in_working_memory:
            retention_eligible = False
            urgency_classification = ReviewUrgency.COOLDOWN_LOCKED
            urgency_score = 0.0
            action_desc = (
                f"Working memory cooldown active ({elapsed_hours:.1f}h / "
                f"{cooldown/3600.0:.1f}h elapsed). Retention retesting locked."
            )
        elif now >= next_review_due:
            retention_eligible = True
            urgency_classification = ReviewUrgency.OVERDUE
            overdue_days = elapsed_days - interval_days
            urgency_score = round(
                min(
                    1.0,
                    0.70
                    + (0.15 * min(2.0, overdue_days / interval_days))
                    + (0.15 * (1.0 - estimated_retention)),
                ),
                4,
            )
            action_desc = (
                f"Retention review overdue by {overdue_days:.1f} days "
                f"(retention: {estimated_retention*100:.1f}%). Schedule retention check."
            )
        elif (next_due_timestamp - now.timestamp()) <= 86400.0:
            retention_eligible = True
            urgency_classification = ReviewUrgency.DUE
            urgency_score = round(min(1.0, 0.50 + 0.30 * (1.0 - estimated_retention)), 4)
            action_desc = "Review due shortly. Eligible for retention verification session."
        else:
            retention_eligible = True
            urgency_classification = ReviewUrgency.UPCOMING
            urgency_score = round(max(0.01, 0.20 * (1.0 - estimated_retention)), 4)
            remaining_d = (next_due_timestamp - now.timestamp()) / 86400.0
            action_desc = (
                f"Retention stable ({estimated_retention*100:.1f}%). "
                f"Next review due in {remaining_d:.1f} days."
            )

        return RetentionScheduleItem(
            objective_id=objective.id,
            objective_code=objective.code,
            objective_title=objective.title,
            mastery_state=mastery_profile.mastery_state,
            performance_score=p_k,
            confidence_score=c_k,
            last_attempt_at=last_attempt_time,
            elapsed_hours=elapsed_hours,
            in_working_memory=in_working_memory,
            retention_eligible=retention_eligible,
            interval_days=round(interval_days, 1),
            next_review_due=next_review_due,
            retention_stability_days=stability_days,
            estimated_retention=estimated_retention,
            urgency_score=urgency_score,
            urgency_classification=urgency_classification,
            recommended_action=action_desc,
            metadata={
                "consecutive_unassisted_correct": consecutive_unassisted_correct,
                "cooldown_seconds": cooldown,
                "elapsed_seconds": round(elapsed_seconds, 1),
            },
        )

    @classmethod
    def build_review_queue(
        cls,
        student_id: str,
        course_id: str,
        items: list[RetentionScheduleItem],
        as_of_time: datetime | None = None,
    ) -> SpacedReviewQueue:
        """Sort and summarize retention schedule items into an actionable review queue."""
        now = as_of_time or datetime.now(UTC)
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)

        priority_order = {
            ReviewUrgency.OVERDUE: 0,
            ReviewUrgency.DUE: 1,
            ReviewUrgency.UPCOMING: 2,
            ReviewUrgency.UNTESTED: 3,
            ReviewUrgency.COOLDOWN_LOCKED: 4,
        }

        sorted_items = sorted(
            items,
            key=lambda item: (
                priority_order.get(item.urgency_classification, 9),
                -item.urgency_score,
                item.next_review_due.timestamp() if item.next_review_due else 0.0,
            ),
        )

        overdue_cnt = sum(1 for it in items if it.urgency_classification == ReviewUrgency.OVERDUE)
        due_cnt = sum(1 for it in items if it.urgency_classification == ReviewUrgency.DUE)
        cooldown_cnt = sum(
            1 for it in items if it.urgency_classification == ReviewUrgency.COOLDOWN_LOCKED
        )

        return SpacedReviewQueue(
            student_id=student_id,
            course_id=course_id,
            as_of_time=now,
            total_objectives_evaluated=len(items),
            overdue_count=overdue_cnt,
            due_count=due_cnt,
            working_memory_locked_count=cooldown_cnt,
            items=sorted_items,
        )

    @classmethod
    def plan_retention_session(
        cls,
        queue: SpacedReviewQueue,
        max_session_items: int = 5,
    ) -> RetentionSessionPlan:
        """Construct a bounded retention session respecting Rule 6 and cognitive budget."""
        eligible_items = [
            item
            for item in queue.items
            if item.retention_eligible
            and item.urgency_classification in (ReviewUrgency.OVERDUE, ReviewUrgency.DUE)
        ]

        if len(eligible_items) < max_session_items:
            upcoming_eligible = [
                item
                for item in queue.items
                if item.retention_eligible and item.urgency_classification == ReviewUrgency.UPCOMING
            ]
            eligible_items.extend(upcoming_eligible[: max_session_items - len(eligible_items)])

        planned = eligible_items[:max_session_items]

        if not planned:
            reason = (
                "No objectives currently require retention review. "
                f"{queue.working_memory_locked_count} items are in working memory cooldown."
                if queue.working_memory_locked_count > 0
                else "All objectives are up to date and retain durable mastery."
            )
        else:
            reason = (
                f"Selected {len(planned)} priority objectives for delayed retention verification. "
                "Evaluates durable mastery decoupled from working memory recall."
            )

        return RetentionSessionPlan(
            student_id=queue.student_id,
            course_id=queue.course_id,
            as_of_time=queue.as_of_time,
            context=AssessmentContext.RETENTION_REVIEW,
            planned_items=planned,
            total_items=len(planned),
            reason=reason,
        )
